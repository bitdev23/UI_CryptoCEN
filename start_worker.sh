#!/usr/bin/env bash
set -euo pipefail

if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
elif [[ -f venv/bin/activate ]]; then
  source venv/bin/activate
fi

python worker.py
