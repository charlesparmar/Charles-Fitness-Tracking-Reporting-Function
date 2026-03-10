#!/usr/bin/env bash
# Run the reporting API (from project root, with venv activated)
set -e
cd "$(dirname "$0")"
export PYTHONPATH=.
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi
python -m src.main "$@"
