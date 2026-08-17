#!/usr/bin/env python3
"""
Compute all metrics from full-population raw data.

Inputs:
  - /workspace/raw_prs_full_population.csv (Search API: author, created_at, closed_at, comments)
  - /workspace/pr_size_data.csv (git: additions, deletions, changed_files)

Outputs:
  - /workspace/monthly_metrics_full.csv (all metrics per project-month)
"""
import pandas as pd
import numpy as np
from datetime import datetime

def assign_era(ym):
    dt = pd.Timestamp(ym)
    if dt < pd.Timestamp("2023-10"): return 0
    if dt < pd.Timestamp("2024-06"): return 1
    if dt < pd.Timestamp("2025-01"): return 2
    return 3

def main():
    # Load raw PR data
    print("Loading raw PR data...")
    prs = pd.read_csv("/workspace/raw_prs_full_population.csv")
    print(f"  {len(prs)} PRs loaded")
    
    # Load PR-size data
    print("Loading PR-size data...")
    sizes = pd.read_csv("/workspace/pr_size_data.csv")
    print(f"  {len(sizes)} PR-size records loaded")
    
    # Merge on project + pr_number
    print("Merging datasets...")
    merged = prs.merge(
        sizes[["project", "pr_number", "additions", "deletions", "changed_files"]],
        on=["project", "pr_number"],
        how="left"
    )
    print(f"  {len(merged)} merged records")
    print(f"  PRs with size data: {merged['additions'].notna().sum()} ({merged['additions'].notna().mean()*100:.1f}%)")
    
    # Compute monthly metrics
    print("Computing monthly metrics...")
    rows = []
    
    for (project, ym), group in merged.groupby(["project", "year_month"]):
        # Metric 1: Throughput (count of merged PRs)
        prs_merged = len(group)
        
        # Metric 2: Cycle time
        cycle_median = group["cycle_days"].median()
        cycle_p90 = group["cycle_days"].quantile(0.9)
        
        # Metric 3: Contributor breadth (unique authors)
        unique_authors = group["author"].nunique()
        
        # Metric 5: Comment density
        comment_mean = group["comments"].mean()
        comment_median = group["comments"].median()
        
        # PR-size metrics
        additions_median = group["additions"].median()
        deletions_median = group["deletions"].median()
        files_median = group["changed_files"].median()
        additions_mean = group["additions"].mean()
        deletions_mean = group["deletions"].mean()
        files_mean = group["changed_files"].mean()
        
        rows.append({
            "project": project,
            "year_month": ym,
            "prs_merged": prs_merged,
            "cycle_median_days": cycle_median,
            "cycle_p90_days": cycle_p90,
            "unique_contributors": unique_authors,
            "comment_mean": comment_mean,
            "comment_median": comment_median,
            "additions_median": additions_median,
            "deletions_median": deletions_median,
            "files_median": files_median,
            "additions_mean": additions_mean,
            "deletions_mean": deletions_mean,
            "files_mean": files_mean,
        })
    
    df = pd.DataFrame(rows)
    
    # Add era
    df["era"] = df["year_month"].apply(assign_era)
    
    # Add date column for plotting
    df["date"] = pd.to_datetime(df["year_month"] + "-01")
    
    # Add month_num for OLS
    df["month_num"] = (df["date"] - df["date"].min()).dt.days / 30.44
    
    # Compute contributor diversity (new vs returning)
    print("Computing contributor diversity...")
    for project in df["project"].unique():
        proj_prs = merged[merged["project"] == project].sort_values("year_month")
        seen = set()
        for ym in sorted(proj_prs["year_month"].unique()):
            month_authors = set(proj_prs[proj_prs["year_month"] == ym]["author"].unique())
            new = len(month_authors - seen)
            returning = len(month_authors & seen)
            ratio = new / (new + returning) if (new + returning) > 0 else np.nan
            
            mask = (df["project"] == project) & (df["year_month"] == ym)
            df.loc[mask, "new_authors"] = new
            df.loc[mask, "returning_authors"] = returning
            df.loc[mask, "new_ratio"] = ratio
            
            seen.update(month_authors)
    
    # Load opened PRs for merge rate
    print("Loading opened PRs for merge rate...")
    # We need to compute this from the original metrics or re-collect
    # For now, use the existing v2 metrics for opened PRs
    try:
        v2 = pd.read_csv("/mnt/results/sglang_vllm_monthly_metrics_v2.csv")
        opened = v2[["project", "year_month", "prs_opened"]].drop_duplicates()
        df = df.merge(opened, on=["project", "year_month"], how="left")
        df["merge_rate"] = df["prs_merged"] / df["prs_opened"]
    except Exception as e:
        print(f"  Warning: could not load opened PRs: {e}")
        df["prs_opened"] = np.nan
        df["merge_rate"] = np.nan
    
    # Save
    out_csv = "/workspace/monthly_metrics_full.csv"
    df.to_csv(out_csv, index=False)
    print(f"\nSaved {len(df)} rows to {out_csv}")
    print()
    print("Summary by project:")
    print(df.groupby("project")[["prs_merged", "unique_contributors", "comment_mean", "additions_median"]].median())

if __name__ == "__main__":
    main()
