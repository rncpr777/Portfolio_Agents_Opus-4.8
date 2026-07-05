"""
Automation script for batch running the portfolio agent.

Run from the project root folder (same level as the `output/` folder and `portfolio_agents/`).

Runs the agent 120 times total:
    - Group 1: 40 runs — low-medium risk, $5,000,  mix of high cap and low cap stocks
    - Group 2: 40 runs — medium-high risk, $15,000, mix of high cap and low cap stocks
    - Group 3: 40 runs — medium risk, $100,000,    mix of high cap and low cap stocks

After all runs, extracts 4 metrics from each portfolio_metrics.json and saves
a single results.csv with 12 columns (4 metrics x 3 groups) and 40 rows.

Usage:
    python batch_run.py
"""

import subprocess
import sys
import os
import json
import csv
import time
import datetime

# ---------------- CONFIG ----------------
RUNS_PER_GROUP = 40
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
OUTPUT_CSV = os.path.join(ROOT_DIR, "results.csv")

GROUPS = [
    {
        "label": "5000_low_medium",
        "capital": "5000",
        "horizon": "10 years",
        "risk": "low-medium",
        "preferences": "mix of high cap and low cap stocks",
    },
    {
        "label": "15000_medium_high",
        "capital": "15000",
        "horizon": "10 years",
        "risk": "medium-high",
        "preferences": "mix of high cap and low cap stocks",
    },
    {
        "label": "100000_medium",
        "capital": "100000",
        "horizon": "10 years",
        "risk": "medium",
        "preferences": "mix of high cap and low cap stocks",
    },
]

METRICS = ["annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown"]
METRIC_LABELS = ["Annualized return", "Annualized volatility", "Sharpe ratio", "Max drawdown"]

GROUP_DISPLAY_NAMES = [
    "5000, low-medium risk",
    "15000, medium-high risk",
    "100000, medium risk",
]

# -----------------------------------------


def get_existing_run_folders():
    """Return set of already-existing datetime folder names in output/."""
    if not os.path.isdir(OUTPUT_DIR):
        return set()
    return set(os.listdir(OUTPUT_DIR))


def run_once(group):
    """Invoke the portfolio agent once with the given group's inputs via stdin."""
    inputs = "\n".join([
        group["capital"],
        group["horizon"],
        group["risk"],
        group["preferences"],
    ]) + "\n"

    result = subprocess.run(
        ["py", "-3.10", "-m", "portfolio_agents"],
        input=inputs,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT_DIR,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )

    if result.returncode != 0:
        print(f"    [WARNING] Process exited with code {result.returncode}")
        print(f"    STDERR: {result.stderr[-500:] if result.stderr else 'none'}")
    else:
        for line in result.stdout.splitlines():
            if "All outputs for this run are saved in" in line:
                print(f"    {line.strip()}")
                break


def get_sorted_run_folders():
    """Return all run folder paths sorted chronologically."""
    if not os.path.isdir(OUTPUT_DIR):
        return []
    entries = [
        os.path.join(OUTPUT_DIR, d)
        for d in os.listdir(OUTPUT_DIR)
        if os.path.isdir(os.path.join(OUTPUT_DIR, d))
    ]
    entries.sort(key=lambda p: os.path.basename(p))
    return entries


def extract_metric(run_folder, metric_key):
    """Extract a single portfolio metric from a run's portfolio_metrics.json."""
    json_path = os.path.join(run_folder, "portfolio_metrics.json")
    if not os.path.exists(json_path):
        print(f"  [WARNING] Missing portfolio_metrics.json in {run_folder}")
        return None
    with open(json_path, "r") as f:
        data = json.load(f)
    value = data.get("portfolio", {}).get(metric_key)
    if value is None:
        print(f"  [WARNING] Metric '{metric_key}' not found in {json_path}")
    return value


def extract_to_csv(folders_by_group):
    """Write results.csv from the collected run folders."""
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)

        # Row 1: group display names, each spanning 4 columns
        row1 = []
        for name in GROUP_DISPLAY_NAMES:
            row1.extend([name, "", "", ""])
        writer.writerow(row1)

        # Row 2: metric labels repeated per group
        writer.writerow(METRIC_LABELS * len(GROUPS))

        # Data rows
        for i in range(RUNS_PER_GROUP):
            row = []
            for group_label in [g["label"] for g in GROUPS]:
                folders = folders_by_group[group_label]
                if i < len(folders):
                    for metric in METRICS:
                        row.append(extract_metric(folders[i], metric))
                else:
                    row.extend([None] * len(METRICS))
            writer.writerow(row)

    print(f"\nSaved {RUNS_PER_GROUP} rows x {len(GROUPS) * len(METRICS)} columns to {OUTPUT_CSV}")


def main():
    if not os.path.isdir(os.path.join(ROOT_DIR, "portfolio_agents")):
        print("ERROR: Run this script from the project root (where portfolio_agents/ folder is).")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    total_runs = RUNS_PER_GROUP * len(GROUPS)
    print(f"\n{'='*55}")
    print(f"  Batch Portfolio Run — {total_runs} total runs")
    print(f"  {RUNS_PER_GROUP} runs x {len(GROUPS)} investor groups")
    print(f"  Outputs → {OUTPUT_DIR}/")
    print(f"{'='*55}\n")

    # Track which folders belong to which group by recording before/after each run
    folders_by_group = {g["label"]: [] for g in GROUPS}

    run_number = 0
    for group in GROUPS:
        print(f"\n--- Group: {group['label']} ({RUNS_PER_GROUP} runs) ---")
        for i in range(RUNS_PER_GROUP):
            run_number += 1
            print(f"  Run {run_number}/{total_runs} (group run {i+1}/{RUNS_PER_GROUP})...")

            existing_before = get_existing_run_folders()
            run_once(group)
            existing_after = get_existing_run_folders()

            # Find the new folder created by this run
            new_folders = existing_after - existing_before
            if new_folders:
                new_folder_name = sorted(new_folders)[-1]  # take latest if somehow multiple
                folders_by_group[group["label"]].append(
                    os.path.join(OUTPUT_DIR, new_folder_name)
                )
            else:
                print(f"  [WARNING] No new output folder detected for run {run_number} — run may have failed.")

            # Small delay to avoid timestamp collisions and rate limits
            time.sleep(2)

    # Verify counts
    print("\n--- Run Summary ---")
    all_ok = True
    for group in GROUPS:
        count = len(folders_by_group[group["label"]])
        status = "OK" if count == RUNS_PER_GROUP else f"WARNING: expected {RUNS_PER_GROUP}"
        print(f"  {group['label']}: {count} successful runs — {status}")
        if count != RUNS_PER_GROUP:
            all_ok = False

    if not all_ok:
        print("\n[WARNING] Some runs may have failed. CSV will still be generated with available data.")

    print(f"\n--- Extracting metrics to {OUTPUT_CSV} ---")
    extract_to_csv(folders_by_group)

    print("\nDone!")


if __name__ == "__main__":
    main()
