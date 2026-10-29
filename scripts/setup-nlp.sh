#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m pip install 'https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl'
printf '%s\n' 'Local English NLP pipeline is ready. Restart ./scripts/dev.sh to load it.'
