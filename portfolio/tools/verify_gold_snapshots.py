#!/usr/bin/env python3
"""Verify downloaded Gold CSVs before the public app can consume them."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


CONTRACTS = {
    "gold_population_summary_2013_2018": {
        "columns": [
            "start_year",
            "end_year",
            "year_count",
            "mean_population",
            "population_stddev",
            "stddev_semantics",
        ],
        "rows": 1,
        "key": ("start_year", "end_year"),
    },
    "gold_bls_best_year_by_series": {
        "columns": [
            "series_id",
            "series_label",
            "best_year",
            "annual_quarterly_sum",
            "quarterly_observation_count",
            "has_quarterly_observations",
        ],
        "rows": 282,
        "key": ("series_id",),
    },
    "gold_bls_q01_population": {
        "columns": [
            "series_id",
            "series_label",
            "year",
            "q01_value",
            "population",
            "population_match_found",
        ],
        "rows": 39,
        "key": ("series_id", "year"),
    },
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def verify(snapshot_dir: Path) -> None:
    manifest_path = snapshot_dir / "snapshot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for name, contract in CONTRACTS.items():
        details = manifest["contracts"].get(name)
        if not details:
            raise ValueError(f"manifest missing {name}")
        path = snapshot_dir / details["file"]
        columns, rows = read_rows(path)
        if columns != contract["columns"]:
            raise ValueError(f"{name}: ordered schema mismatch")
        if len(rows) != contract["rows"] or details["row_count"] != len(rows):
            raise ValueError(f"{name}: row-count mismatch")
        observed_digest = digest(path)
        if observed_digest != details["sha256"]:
            raise ValueError(f"{name}: SHA-256 mismatch")
        keys = [tuple(row[column] for column in contract["key"]) for row in rows]
        if len(keys) != len(set(keys)):
            raise ValueError(f"{name}: duplicate business key")

    q1_path = snapshot_dir / manifest["contracts"]["gold_population_summary_2013_2018"]["file"]
    _, q1_rows = read_rows(q1_path)
    q1 = q1_rows[0]
    if (q1["start_year"], q1["end_year"], q1["year_count"]) != ("2013", "2018", "6"):
        raise ValueError("Question 1 bounds or year count mismatch")

    q3_path = snapshot_dir / manifest["contracts"]["gold_bls_q01_population"]["file"]
    _, q3_rows = read_rows(q3_path)
    matches = sum(row["population_match_found"].lower() == "true" for row in q3_rows)
    if matches != 11:
        raise ValueError("Question 3 must contain exactly 11 population matches")

    print(
        f"PASS: verified snapshot {manifest['snapshot_id']} "
        "(1 / 282 / 39 rows; schemas, keys, match counts, and digests valid)"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot_dir", type=Path)
    args = parser.parse_args()
    verify(args.snapshot_dir.resolve())


if __name__ == "__main__":
    main()

