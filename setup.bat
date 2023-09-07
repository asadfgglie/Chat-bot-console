@echo off
cd files
echo installing dependencies...
python -m pip install --upgrade pip
python -m pip install --user virtualenv
echo creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt
python "UI.py"
@Pause