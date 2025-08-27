@echo off
setlocal
if not exist .venv (
  py -m venv .venv
)
call .\.venv\Scripts\activate
pip install -r requirements.txt
set ECS_HOST=127.0.0.1
set ECS_PORT=8080
python main.py
pause
