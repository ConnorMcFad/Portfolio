"""Load the raw Adzuna pages saved by collector.py and build one tidy DataFrame.

Usage:  python clean.py [input_dir] [output_file]
Defaults: data/raw  data/clean/postings.parquet
Raw files are named <search>_p<page>.json; the search label comes from the file name.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

# Columns kept from pd.json_normalize. Dotted names are nested fields it flattened,
# e.g. company.display_name. reindex() below guarantees they all exist and drops
# everything else (__CLASS__, adref, stray null columns).
KEEP = [
    "id", "title", "description", "created", "salary_min", "salary_max",
    "salary_is_predicted", "latitude", "longitude", "contract_type",
    "contract_time", "redirect_url", "company.display_name",
    "location.display_name", "location.area", "category.label",
    "search", "source_file",
]
# One capture group: "$75,000 - $88,000", "$50-60/HR", "$35.00/hour", "$95,000"
PAY_PATTERN = (
    r"(\$\d[\d,.]*[kK]?"                          # $75,000  or  $50  or  $95k
    r"(?:\s?(?:-|\u2013|to)\s?\$?\d[\d,.]*[kK]?)?"  # optional range end: - $88,000
    r"(?:\s?(?:/|per)\s?(?:hr|hour|yr|year))?)"    # optional unit: /hr, per year
)


def load_raw(input_dir: Path) -> pd.DataFrame:
    """Read every saved page and flatten its postings into one DataFrame."""
    pages = []
    for path in sorted(input_dir.glob("*.json")):
        results = json.loads(path.read_text()).get("results", [])
        if results:
            page = pd.json_normalize(results)
            page["search"] = path.stem.rsplit("_p", 1)[0]  # data_analyst_p001 -> data_analyst
            page["source_file"] = path.name
            pages.append(page)
    if not pages:
        raise SystemExit(f"No postings found in {input_dir}")
    return pd.concat(pages, ignore_index=True)


def tidy(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.reindex(columns=KEEP).dropna(subset=["id"]).copy()

    # De-duplicate: a posting found by both searches is kept once, with both labels
    df["id"] = df["id"].astype(str)
    df["searches"] = df.groupby("id")["search"].transform(lambda s: ",".join(sorted(set(s))))
    df = df.drop_duplicates(subset="id").drop(columns="search")

    # location.area stays a list like ["US", "Texas", "Harris County", "Houston"]. Its depth
    # varies, but position 1 is the state:  df["location.area"].str[1]

    # Dates
    df["created"] = pd.to_datetime(df["created"], utc=True, errors="coerce")
    df["created_date"] = df["created"].dt.strftime("%Y-%m-%d")

    # Description snippet: strip tags, the repeated "Job Description" heading, extra spaces
    df["description"] = (
        df["description"]
        .str.replace(r"<[^>]+>", " ", regex=True)
        .str.replace(r"^\s*(?:job description\s*)+", "", case=False, regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    df["desc_len"] = df["description"].str.len()
    df["desc_truncated"] = df["description"].str.endswith("\u2026", na=False)

    # Pay mentioned in the snippet text (separate from Adzuna's own salary fields)
    df["pay_text"] = (
        df["description"].str.extract(PAY_PATTERN, flags=re.I, expand=False).str.rstrip(".,")
    )
    df["pay_is_hourly"] = df["pay_text"].str.contains(r"hr|hour", case=False, na=False)

    # Adzuna salary fields
    for col in ["salary_min", "salary_max"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").where(lambda s: s > 0)
    df["salary_is_predicted"] = pd.to_numeric(df["salary_is_predicted"], errors="coerce")  # arrives as the string "1"/"0"
    df["salary_mid"] = df[["salary_min", "salary_max"]].mean(axis=1)

    return df.reset_index(drop=True)


def summarize(raw: pd.DataFrame, df: pd.DataFrame) -> None:
    print(f"Rows loaded: {len(raw)}   after de-duplication: {len(df)}")
    print("\nMissing share (columns with any missing):")
    print(df.isna().mean().round(2).loc[lambda s: s > 0].to_string())
    print(f"\nSalary flagged as predicted: {df['salary_is_predicted'].mean():.0%}")
    print(f"Pay mentioned in snippet: {df['pay_text'].notna().sum()} postings")
    print(f"Snippet truncated: {df['desc_truncated'].mean():.0%}; length in characters:")
    print(df["desc_len"].describe().round(0).to_string())
    print("\nTop states:")
    print(df["location.area"].str[1].value_counts(dropna=False).head(8).to_string())
    print("\nCreated dates:")
    print(df["created_date"].value_counts().head(5).to_string())
    print("\nTitles:")
    print(df["title"].value_counts().head(8).to_string())


def run(input_dir: Path, output_file: Path) -> pd.DataFrame:
    """Raw JSON pages in input_dir -> cleaned DataFrame, saved to output_file."""
    raw = load_raw(input_dir)
    df = tidy(raw)
    summarize(raw, df)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_file, index=False)
    print(f"\nSaved {len(df)} rows to {output_file}")
    return df


def main() -> None:
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw")
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/clean/postings.parquet")
    run(input_dir, output_file)


if __name__ == "__main__":
    main()