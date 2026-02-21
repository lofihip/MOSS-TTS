#!/usr/bin/env bash
set -e

ENV_NAME="moss-tts"
REPO_DIR="$HOME/MOSS-TTS"
MAIN_APP="clis/moss_tts_app.py"

# Инициализация conda
CONDA_BASE=$(conda info --base 2>/dev/null || echo "$HOME/miniconda3")
source "$CONDA_BASE/etc/profile.d/conda.sh"

# Создаём окружение если нет
if ! conda env list | grep -q "^$ENV_NAME "; then
    echo "Создаём conda-окружение $ENV_NAME ..."
    conda create -n "$ENV_NAME" python=3.12 -y
fi

conda activate "$ENV_NAME"

# Клонируем репозиторий если нет
if [ ! -d "$REPO_DIR" ]; then
    echo "Клонируем репозиторий в $REPO_DIR ..."
    git clone https://github.com/lofihip/MOSS-TTS.git "$REPO_DIR"
fi

cd "$REPO_DIR"

# Устанавливаем пакет если не установлен
if [ ! -d "src/moss_tts.egg-info" ] && [ ! -d "moss_tts.egg-info" ]; then
    echo "Устанавливаем пакет..."
    pip install --extra-index-url https://download.pytorch.org/whl/cu128 -e .
fi

echo ""
echo "Запускаем MOSS-TTS Gradio интерфейс → http://127.0.0.1:7860"
echo ""
python "$MAIN_APP"
