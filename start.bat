@echo off
echo Loading...
cd files
call .venv\Scripts\activate.bat
set OPENAI_API_BASE=http://127.0.0.1:5001/v1
set OPENAI_API_KEY=sk-111111111111111111111111111111111111111111111111
python "UI.py"
@pause
