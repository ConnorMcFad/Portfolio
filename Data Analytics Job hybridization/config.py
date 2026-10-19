"""Central settings for the Adzuna collection.

Secrets come from .env (never commit it). Everything else lives here so the
collector has no hard-coded parameters.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

COUNTRY = "us"
BASE_SEARCH_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"

# label -> params merged into every request for that search.
# The label becomes part of each raw file name (<label>_p<page>.json).
SEARCHES = {
    "data_analyst": {"title_only": "data analyst"},
    "data_scientist": {"title_only": "data scientist"},
}

# Sent with every request. Do not add salary_min/salary_max filters here:
# they can exclude postings without a known salary.
COMMON_PARAMS = {
    "results_per_page": 50,
    "max_days_old": 30,
    "content-type": "application/json",
}

# Pages to request per search. Pages 1..N are the head of Adzuna's default
# ordering, not a random sample; spread the numbers out (e.g. 1, 10, 20, ...)
# once you know how deep the API lets you page.
PAGES = list(range(1, 11))

CALL_CAP = 25         # hard stop; raise only after your plan changes
REQUEST_DELAY = 3.0   # seconds between calls (ToS default: 25 hits/minute)

RAW_DIR = Path("data/raw")
LOG_FILE = Path("data/call_log.txt")
CLEAN_FILE = Path("data/clean/postings.parquet")