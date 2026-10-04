#!/usr/bin/env bash
set -e
python3 -m pip install -q -r requirements.txt
exec python3 -m uvicorn app.main:app --port 8000
