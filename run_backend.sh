#!/usr/bin/env bash
set -e
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r Code/backend/requirements.txt
python -m uvicorn Code.backend.app:app --reload
