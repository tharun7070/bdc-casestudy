@echo off
setlocal
if not exist venv python -m venv venv
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist data\events.csv (
  python download_dataset.py
)
python run_analysis.py
streamlit run app.py
