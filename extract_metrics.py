"""
Run this script from inside a project's root folder (same level as the `output/` folder).

It reads all run subfolders inside `output/` (datetime-named), sorts them chronologically,
splits them into 3 consecutive blocks of 17 runs each:
    Block 1 (runs 1-17):  5000, low-medium risk
    Block 2 (runs 18-34): 15000, medium-high risk
    Block 3 (runs 35-51): 100000, medium risk

For each run, extracts 4 metrics from portfolio_metrics.json ("portfolio" section):
    annualized_return, annualized_volatility, sharpe_ratio, max_drawdown

Output: a single CSV (results.csv) with 12 columns (4 metrics x 3 groups) and 17 rows,
with a top header row naming the groups and a second header row naming the metrics -
matching the requested spreadsheet layout.

Usage:
    python extract_metrics.py
"""

import json
import os
import csv

# ---------------- CONFIG ----------------
RUNS_PER_GROUP = 17
GROUPS = [
    "5000, low-medium risk",
    "15000, medium-high risk",
    "100000, medium risk",
]
METRICS = ["annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown"]
METRIC_LABELS = ["Annualized return", "Annualized volatility", "Sharpe ratio", "Max drawdown"]
OUTPUT_DIR = "output"
OUTPUT_CSV = "results.csv"
# -----------------------------------------


def get_sorted_run_folders(output_root):
    entries = [
        os.path.join(output_root, d)
        for d in os.listdir(output_root)
        if os.path.isdir(os.path.join(output_root, d))
    ]
    entries.sort(key=lambda p: os.path.basename(p))
    return entries


def extract_run_metrics(run_folder):
    json_path = os.path.join(run_folder, "portfolio_metrics.json")
    if not os.path.exists(json_path):
        print(f"WARNING: missing portfolio_metrics.json in {run_folder}")
        return {m: None for m in METRICS}
    with open(json_path, "r") as f:
        data = json.load(f)
    portfolio = data.get("portfolio", {})
    result = {}
    for m in METRICS:
        value = portfolio.get(m)
        if value is None:
            print(f"WARNING: metric '{m}' not found in {json_path}")
        result[m] = value
    return result


def main():
    if not os.path.isdir(OUTPUT_DIR):
        print(f"ERROR: '{OUTPUT_DIR}' folder not found. Run this script from the project root.")
        return

    folders = get_sorted_run_folders(OUTPUT_DIR)
    expected_total = RUNS_PER_GROUP * len(GROUPS)
    if len(folders) != expected_total:
        print(f"WARNING: found {len(folders)} run folders, expected {expected_total}")

    # group_data[group_name] = list of 17 dicts (one per run), each {metric: value}
    group_data = {}
    for i, group in enumerate(GROUPS):
        start = i * RUNS_PER_GROUP
        end = start + RUNS_PER_GROUP
        chunk = folders[start:end]
        group_data[group] = [extract_run_metrics(f) for f in chunk]

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)

        # Row 1: group names, each spanning 4 columns (merged visually via blanks)
        row1 = []
        for group in GROUPS:
            row1.extend([group, "", "", ""])
        writer.writerow(row1)

        # Row 2: metric labels repeated per group
        row2 = []
        for _ in GROUPS:
            row2.extend(METRIC_LABELS)
        writer.writerow(row2)

        # Data rows
        for i in range(RUNS_PER_GROUP):
            row = []
            for group in GROUPS:
                run = group_data[group][i]
                row.extend([run[m] for m in METRICS])
            writer.writerow(row)

    print(f"\nSaved {RUNS_PER_GROUP} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
