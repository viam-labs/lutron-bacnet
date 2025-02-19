#!/bin/sh
cd "$(dirname "$0")" || exit

# Create a virtual environment to run our code
VENV_NAME=".venv"

export PATH="$PATH:$HOME/.local/bin"

if [ ! "$(command -v uv)" ]; then
  if [ ! "$(command -v curl)" ]; then
    echo "curl is required to install UV. please install curl on this system to continue."
    exit 1
  fi
  echo "Installing uv command"
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

if ! uv venv $VENV_NAME; then
  echo "unable to create required virtual environment"
  exit 1
fi

if ! uv pip install -r requirements.txt; then
  echo "unable to sync requirements to venv"
  exit 1
fi
