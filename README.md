# ShopTrace — Real E-Commerce Clickstream Analytics

**A Big Data Computing case study using the real Retailrocket e-commerce event dataset.**

ShopTrace analyzes anonymized real-world product interaction events to understand browsing behaviour, product popularity, customer journeys, session exits and conversion drop-off.

## Dataset (real data, not synthetic)

Source: [Retailrocket E-commerce Dataset on Kaggle](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset)

The original publication describes 2,756,101 events from 1,407,580 unique visitors over approximately 4.5 months:
- 2,664,312 `view` events
- 69,332 `addtocart` events
- 22,457 `transaction` events

The data is anonymized. It contains product interaction events, not page URLs, device types, customer names or payment details.

**Dataset licence:** CC BY-NC-SA 4.0. Review the source terms before redistributing. This repository intentionally does not bundle the raw dataset; download it directly from Kaggle.

## What the project measures

1. Total events and unique visitors.
2. Sessions created using a 30-minute inactivity rule.
3. Single-event session rate (a clearly defined bounce proxy).
4. Most viewed, carted and purchased products.
5. Product-to-product navigation transitions.
6. Product on which each session ended (exit product, not URL exit page).
7. Session conversion funnel: view → add-to-cart → transaction.
8. Cart-session abandonment proxy.
9. Hourly and daily event activity.

## Quick start — Windows

### Prerequisites
- Python 3.10 or newer.
- Internet access for dependency and dataset download.
- A free Kaggle account and Kaggle API token.

### Step 1 — Download this repository
Download the ZIP from GitHub and extract it, or clone the repository.

### Step 2 — Configure Kaggle API (one-time setup)
1. Sign in to Kaggle.
2. Open your account settings: https://www.kaggle.com/settings
3. Under API, create a new token and download `kaggle.json`.
4. Create this folder if it does not exist: `%USERPROFILE%\\.kaggle`
5. Move `kaggle.json` into that folder.

Keep `kaggle.json private. Never upload it to GitHub or share it with classmates.

### Step 3 — Run the project
Double-click `run_windows.bat`.

Or open a terminal in the project folder and run:

```powershell
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
python download_dataset.py
python run_analysis.py
streamlit run app.py
```

Open the local Streamlit URL printed in the terminal, normally http://localhost:8501.

## macOS / Linux

Configure the Kaggle API token at `~/.kaggle/kaggle.json`, then:

```bash
chmod +x run_mac_linux.sh
./run_mac_linux.sh
```

## Manual dataset download alternative

If Kaggle API setup is inconvenient:
1. Open the Kaggle dataset link above.
2. Download the dataset archive.
3. Extract only `events.csv`.
4. Place it at `data/events.csv`.
5. Run `python run_analysis.py`, then `streamlit run app.py`.

The download script requests only `events.csv`, not the large item-properties files.

## How the processing works

- DuckDB reads and queries the raw CSV efficiently.
- Invalid rows and unknown event types are excluded.
- Events are sorted by visitor and timestamp.
- A new session begins when the gap between consecutive events for the same visitor is greater than 30 minutes.
- SQL window functions derive sessions, last events and next-product transitions.
- Aggregated CSV reports feed the Streamlit dashboard.

## Metric definitions (important for your viva)

**Session:** Events from the same visitor separated by no more than 30 minutes of inactivity. A gap greater than 30 minutes starts a new session.

**Single-event session rate:** Sessions containing exactly one recorded event divided by all sessions. This is a practical bounce proxy for this event dataset; it is not guaranteed to match Google Analytics' bounce-rate definition.

**Exit product:** The item ID in the final recorded event of a session. This is not a page URL.

**Navigation transition:** A product view followed by the next product view in the same derived session.

**Conversion funnel:** Counts sessions that contain at least one view, add-to-cart or transaction event. Stage counts are not necessarily mutually exclusive.

**Cart-session abandonment rate:** Among sessions containing at least one add-to-cart event, the percentage without a transaction event in that same session. This is a session-level proxy, not a definitive order-level abandonment metric.

## Big Data concepts demonstrated

| BDC concept | Implementation |
|---|---|
| Volume | 2.75 million real event records |
| Velocity | Timestamped event stream analysis (offline batch) |
| Variety | Event types and interaction records |
| Data ingestion | CSV ingestion |
| Data cleaning | Type conversion and invalid-row filtering |
| Sessionization | SQL window functions |
| Batch processing | DuckDB analytical queries |
| Parallel/distributed extension | Optional PySpark implementation |
| Data visualization | Streamlit and Plotly |

**Important:** The main quick-start uses DuckDB for local analytical processing. `spark_analysis.py` is an optional Spark local-mode extension. Local Spark mode is not a multi-node Hadoop cluster. Do not claim that this project runs a real distributed Hadoop cluster unless you configure one separately.

## Project structure

```text
ShopTrace-Real-Clickstream/
├── app.py
├── download_dataset.py
├── run_analysis.py
├── spark_analysis.py
├── requirements.txt
├── run_windows.bat
├── run_mac_linux.sh
├── README.md
├── data/
│   └── README.md
└── outputs/
    └── README.md
```

## 20–30 minute classroom target

| Time | Task |
|---|---|
| 0–5 min | Extract project and configure Kaggle token (token setup should be done beforehand) |
| 5–10 min | Install Python packages |
| 10–15 min | Download `events.csv` |
| 15–22 min | Run analysis |
| 22–30 min | Launch dashboard and explain results |

Actual time depends on internet speed, Kaggle access and computer performance. For a smooth classroom session, the instructor should download the dataset and pre-run the analysis before the presentation.

## Privacy and responsible use

The published dataset is anonymized. Do not add real personal information, credentials, payment data or API tokens to this repository. Keep `kaggle.json` private.

## Citation

Retailrocket. *Retailrocket recommender system dataset*. Kaggle. https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset

Dataset description and licence are provided on the original Kaggle page.
