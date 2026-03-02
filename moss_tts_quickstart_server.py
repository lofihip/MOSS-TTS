from __future__ import annotations

import io
import tempfile
import uuid
from pathlib import Path

import soundfile as sf
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from transformers import AutoModelForCausalLM, AutoProcessor


DEFAULT_MODEL = "OpenMOSS/MOSS-TTS-Preview"

app = FastAPI(title="MOSS-TTS Quickstart REST", version="1.0.0")

_processor: AutoProcessor | None = None
_model: AutoModelForCausalLM | None = None
_device: str = "cuda" if torch.cuda.is_available() else "cpu"


def _load_once(model_name: str = DEFAULT_MODEL) -> None:
    global _processor, _model, _device
    if _processor is not None and _model is not None:
        return

    _processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    _model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
    _model.eval()
    _model.to(_device)


@app.on_event("startup")
def _startup() -> None:
    _load_once()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "device": _device}


@app.post("/tts")
def tts(
    text: str = Form(...),
    reference_text: str = Form(""),
    duration_control: float = Form(...),
    reference_audio: UploadFile = File(...),
) -> Response:
    if not text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    if _processor is None or _model is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    suffix = Path(reference_audio.filename or "ref.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(reference_audio.file.read())
        ref_path = Path(tmp.name)

    try:
        duration_tokens = max(1, int(float(duration_control) * 12.5))
        user_kwargs: dict = {
            "text": text.strip(),
            "reference": [str(ref_path)],
            "tokens": duration_tokens,
        }
        if reference_text.strip():
            user_kwargs["reference_text"] = reference_text.strip()

        conversation = [[_processor.build_user_message(**user_kwargs)]]
        batch = _processor(conversation, mode="generation")
        for key, value in list(batch.items()):
            if hasattr(value, "to"):
                batch[key] = value.to(_model.device)

        max_new_tokens = min(8192, max(256, int(duration_tokens * 2.2)))
        with torch.no_grad():
            output_ids = _model.generate(
                **batch,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                top_p=0.8,
                temperature=0.7,
                repetition_penalty=1.1,
            )

        decoded = _processor.decode(output_ids)
        if not decoded:
            raise RuntimeError("MOSS decode returned empty output.")
        audio = decoded[0].audio_codes_list[0]
        audio_np = audio.detach().float().cpu().numpy()
        sample_rate = int(_processor.model_config.sampling_rate)

        wav_io = io.BytesIO()
        sf.write(wav_io, audio_np, sample_rate, format="WAV")
        wav_bytes = wav_io.getvalue()
        generated_duration = float(len(audio_np)) / float(sample_rate) if sample_rate > 0 else duration_control

        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={"X-Duration-Seconds": f"{generated_duration:.6f}"},
        )
    except Exception as exc:
        return JSONResponse(status_code=500, content={"detail": f"MOSS inference failed: {exc}"})
    finally:
        ref_path.unlink(missing_ok=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("scripts.moss_tts_quickstart_server:app", host="0.0.0.0", port=7860, reload=False)
