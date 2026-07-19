@echo off
python -m venv .venv
call .venv\Scripts\activate
python -m pip install -r Code\backend\requirements.txt
python -m uvicorn Code.backend.app:app --reload
