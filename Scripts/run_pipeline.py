#!/usr/bin/env python3
"""
Master pipeline to reproduce all results from raw data.

Usage:
    python run_pipeline.py [--skip-collect] [--skip-figures]

Steps:
    1. Collect full-population PR data via GitHub Search API (slow, ~60 min)
    2. Extract PR-size data from git clones (requires git, ~5 min)
    3. Compute monthly metrics from raw data
    4. Generate all 7 figures at 500 dpi

Inputs (if --skip-collect):
    - raw_prs_full_population.csv  (from step 1)
    - pr_size_data.csv             (from step 2)

Outputs:
    - monthly_metrics_full.csv     (all metrics per project-month)
    - fig1_..._v3.png through fig7_..._v3.png  (500 dpi)

Requirements:
    pip install pandas numpy matplotlib scipy requests python-dateutil
    git (for PR-size extraction)
"""
import argparse
import os
import subprocess
import sys
import time

def run_step(name, cmd, skip=False):
    """Run a pipeline step, printing status."""
    if skip:
        print(f"\n{'='*60}")
        print(f"  SKIPPING: {name}")
        print(f"{'='*60}")
        return True

    print(f"\n{'='*60}")
    print(f"  RUNNING: {name}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    start = time.time()
    result = subprocess.run(cmd, capture_output=False, text=True)
    elapsed = time.time() - start

    if result.returncode == 0:
        print(f"\n  ✓ {name} completed in {elapsed:.1f}s")
        return True
    else:
        print(f"\n  ✗ {name} FAILED (exit code {result.returncode})")
        return False

def main():
    parser = argparse.ArgumentParser(description="Reproduce all results from raw data")
    parser.add_argument("--skip-collect", action="store_true",
                        help="Skip data collection (use existing CSVs)")
    parser.add_argument("--skip-figures", action="store_true",
                        help="Skip figure generation")
    parser.add_argument("--data-dir", default=".",
                        help="Directory containing raw data CSVs")
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 60)
    print("  Free Code, Expensive Judgment — Reproduction Pipeline")
    print("=" * 60)
    print(f"  Data directory: {data_dir}")
    print(f"  Script directory: {script_dir}")
    print(f"  Skip collect: {args.skip_collect}")
    print(f"  Skip figures: {args.skip_figures}")

    # Step 1: Collect full-population PR data
    if not args.skip_collect:
        ok = run_step(
            "Step 1: Collect full-population PR data via GitHub Search API",
            [sys.executable, os.path.join(script_dir, "collect_full_population.py")],
        )
        if not ok:
            print("Pipeline failed at Step 1")
            sys.exit(1)

    # Step 2: Extract PR-size data from git clones
    if not args.skip_collect:
        print("\n" + "=" * 60)
        print("  Step 2: Extract PR-size data from git clones")
        print("=" * 60)
        print("  This step requires cloning both repositories.")
        print("  Run the following commands manually:")
        print()
        print("    git clone https://github.com/vllm-project/vllm.git /tmp/vllm_full")
        print("    git clone https://github.com/sgl-project/sglang.git /tmp/sglang_full")
        print("    cd /tmp/vllm_full && git log --shortstat --format='COMMIT %H %aI %s' > /tmp/vllm_shortstat.txt")
        print("    cd /tmp/sglang_full && git log --shortstat --format='COMMIT %H %aI %s' > /tmp/sglang_shortstat.txt")
        print()
        print("  Then parse the shortstat files to extract PR-size data.")
        print("  See pr_size_data.csv for the expected output format.")
        print()
        print("  Skipping automated execution (requires manual git operations).")

    # Step 3: Compute monthly metrics
    ok = run_step(
        "Step 3: Compute monthly metrics from raw data",
        [sys.executable, os.path.join(script_dir, "compute_metrics.py")],
    )
    if not ok:
        print("Pipeline failed at Step 3")
        sys.exit(1)

    # Step 4: Generate figures
    if not args.skip_figures:
        ok = run_step(
            "Step 4: Generate all 7 figures at 500 dpi",
            [sys.executable, os.path.join(script_dir, "generate_figures_v3.py")],
        )
        if not ok:
            print("Pipeline failed at Step 4")
            sys.exit(1)

    # Summary
    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)

    # Verify outputs
    outputs = [
        "monthly_metrics_full.csv",
        "fig1_pr_throughput_timeseries_v3.png",
        "fig2_pr_cycle_time_comparison_v3.png",
        "fig3_contributor_breadth_scatter_regression_v3.png",
        "fig4_metrics_heatmap_v3.png",
        "fig5_pr_comment_density_v3.png",
        "fig6_contributor_diversity_v3.png",
        "fig7_pr_size_analysis_v3.png",
    ]

    print("\n  Output verification:")
    all_ok = True
    for f in outputs:
        path = os.path.join(data_dir, f)
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"    ✓ {f} ({size:,} bytes)")
        else:
            # Check /mnt/results/ as well
            alt = os.path.join("/mnt/results", f)
            if os.path.exists(alt):
                size = os.path.getsize(alt)
                print(f"    ✓ {f} ({size:,} bytes, in /mnt/results/)")
            else:
                print(f"    ✗ {f} — NOT FOUND")
                all_ok = False

    if all_ok:
        print("\n  All outputs verified successfully.")
    else:
        print("\n  WARNING: Some outputs are missing.")

if __name__ == "__main__":
    main()
