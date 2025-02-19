#!/bin/sh
cd "$(dirname "$0")" || exit

export PATH="$PATH:$HOME/.local/bin"

if ! uv pip install pyinstaller -q; then
  exit 1
fi

uv run pyinstaller --onefile --add-data=".venv/lib/python3.11/site-packages/BAC0/core/app/device.json:." src/main.py
tar -czvf dist/archive.tar.gz ./dist/main meta.json
