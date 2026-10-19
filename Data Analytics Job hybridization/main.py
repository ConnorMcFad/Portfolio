"""Run the whole pipeline: collect raw pages, then clean them.

    python main.py                 # collect missing pages (spends API calls), then clean
    python main.py --clean-only    # skip the API; just re-clean what is already in data/raw
"""
import logging
import sys

import clean
import collector
import config


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Stage 1 - intake: API -> data/raw/<search>_pNNN.json (pages already on disk are skipped)
    if "--clean-only" not in sys.argv:
        collector.collect()

    # Stage 2 - JSON -> DataFrame -> cleaned Parquet file
    clean.run(config.RAW_DIR, config.CLEAN_FILE)


if __name__ == "__main__":
    main()