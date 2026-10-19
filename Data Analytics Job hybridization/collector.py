"""collector.py - talks to the Adzuna API and saves raw pages to disk.

Single responsibility: HTTP in, raw JSON files out. No pandas, no cleaning.
Every page is written to data/raw/ as soon as it arrives, and pages already
on disk are skipped, so a crash or a rerun never re-spends API calls.

Note: Adzuna returns only a ~500-character snippet of each job description,
not the full text (see the search docs).
"""

import json
import logging
import time
from datetime import datetime, timezone

import requests

import config

log = logging.getLogger(__name__)


class CallBudgetExceeded(RuntimeError):
    """Raised when the logged call count reaches config.CALL_CAP."""


def calls_used() -> int:
    if not config.LOG_FILE.exists():
        return 0
    return len(config.LOG_FILE.read_text().splitlines())


def _log_call(status: int) -> None:
    config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with config.LOG_FILE.open("a") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} status={status}\n")


def _get(url: str, params: dict) -> dict | None:
    """One GET request; returns parsed JSON or None."""
    if calls_used() >= config.CALL_CAP:
        raise CallBudgetExceeded(f"Call cap reached ({config.CALL_CAP}).")
    try:
        resp = requests.get(url, params=params, timeout=30)
    except requests.RequestException as exc:
        log.error("Network problem (%s); no response received", type(exc).__name__)
        return None

    _log_call(resp.status_code)  # count every real response, to be conservative

    if resp.status_code == 200:
        try:
            return resp.json()
        except ValueError:
            log.error("Response was not valid JSON")
            return None
    if resp.status_code in (401, 403):
        log.error("%d: credentials rejected or account not approved", resp.status_code)
    elif resp.status_code == 429:
        log.error("429: rate limited. Stopping; wait before running again.")
    else:
        log.error("HTTP %d: %s", resp.status_code, resp.text[:200])
    return None


def page_path(search: str, page: int):
    return config.RAW_DIR / f"{search}_p{page:03d}.json"


def fetch_page(search: str, page: int) -> dict | None:
    """Return one page from disk if saved, otherwise from the API (and save it)."""
    path = page_path(search, page)
    if path.exists():
        log.info("[%s] page %d already on disk; skipping", search, page)
        return json.loads(path.read_text())

    url = config.BASE_SEARCH_URL.format(country=config.COUNTRY, page=page)
    params = {
        "app_id": config.ADZUNA_APP_ID,
        "app_key": config.ADZUNA_APP_KEY,
        **config.COMMON_PARAMS,
        **config.SEARCHES[search],
    }
    data = _get(url, params)
    if data is None:
        return None

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    time.sleep(config.REQUEST_DELAY)
    return data


def collect() -> None:
    if not config.ADZUNA_APP_ID or not config.ADZUNA_APP_KEY:
        raise SystemExit("Missing ADZUNA_APP_ID / ADZUNA_APP_KEY in .env")

    for search in config.SEARCHES:
        for page in config.PAGES:
            try:
                data = fetch_page(search, page)
            except CallBudgetExceeded as exc:
                log.error("%s Stopping.", exc)
                return
            if data is None:
                log.error("[%s] request failed at page %d; stopping run", search, page)
                return
            results = data.get("results", [])
            if not results:
                log.info("[%s] page %d is empty; moving to next search", search, page)
                break
            log.info("[%s] page %d: %d postings", search, page, len(results))
    log.info("Done. Calls logged: %d/%d", calls_used(), config.CALL_CAP)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    collect()