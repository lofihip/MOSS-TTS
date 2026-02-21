#!/usr/bin/env bash
# Минимальный скрипт: установка + автозапуск MOSS-TTS (moss_tts_app.py)
# Работает и при первой установке, и при повторном запуске

set -e

ENV_NAME="moss-tts"
REPO_DIR="/workspace/MOSS-TTS"                # ← можно изменить на желаемый путь
MAIN_APP="clis/moss_tts_app.py"          # основной Gradio-интерфейс MOSS-TTS

# ─── 1. Проверяем / создаём окружение ───────────────────────────────────────
if ! conda env list | grep -q "$ENV_NAME"; then
    echo "Создаём conda-окружение $ENV_NAME ..."
    conda create -n "$ENV_NAME" python=3.12 -y
fi

# Активируем (в скрипте используем conda shell-хак)
source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null || true
conda activate "$ENV_NAME" || { echo "Ошибка активации $ENV_NAME"; exit 1; }

# ─── 2. Клонируем / обновляем репозиторий ────────────────────────────────────
if [ ! -d "$REPO_DIR" ]; then
    echo "Клонируем репозиторий в $REPO_DIR ..."
    git clone https://github.com/lofihip/MOSS-TTS.git "$REPO_DIR"
fi

cd "$REPO_DIR" || { echo "Не удалось перейти в $REPO_DIR"; exit 1; }

# Простая проверка — установлен ли пакет (есть ли .egg-info или dist-info)
if [ ! -d "src/moss_tts.egg-info" ] && [ ! -d "moss_tts.egg-info" ]; then
    echo "Устанавливаем пакет (pip install -e .) ..."
    pip install --extra-index-url https://download.pytorch.org/whl/cu128 -e .
fi

# ─── 3. Запуск основного приложения ──────────────────────────────────────────
echo ""
echo "Запускаем MOSS-TTS Gradio интерфейс..."
echo "Браузер должен открыться автоматически → http://127.0.0.1:7860"
echo "(модель скачается автоматически при первом запуске)"
echo ""

python "$MAIN_APP"

# Если хотите другую демку — замените строку выше на одну из:
# python clis/moss_ttsd_app.py
# python clis/moss_voice_generator_app.py
# python clis/moss_sound_effect_app.py
