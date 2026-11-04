#!/usr/bin/env bash
set -e
if [ ! -d venv ]; then python3 -m venv venv; fi
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if [ ! -f data/events.csv ]; then python download_dataset.py; fi
python run_analysis.py
streamlit run app.py
