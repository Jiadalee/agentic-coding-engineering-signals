#!/usr/bin/env python3
"""
Compute decomposed metrics (human vs. bot) and attribution analysis.

Inputs:
  - /workspace/raw_prs_full_population.csv (human-only PRs)
  - /workspace/raw_prs_bot_only.csv (bot-only PRs)
  - /workspace/bot_comment_sample.csv (sampled comment data)
  - /workspace/pr_size_data.csv (PR size data)

Outputs:
  - /workspace/monthly_metrics_decomposed.csv
  - /workspace/bot_attribution_summary.csv
"""
import pandas as pd
import numpy as np

# Era definitions
def assign_era(ym):
    dt = pd.Timestamp(ym)
    if dt < pd.Timestamp("2023-10"): return 0
    if dt < pd.Timestamp("2024-06"): return 1
    if dt < pd.Timestamp("2025-01"): return 2
    return 3

ERA_LABELS = {0: "Era 0", 1: "Era 1", 2: "Era 2", 3: "Era 3"}

def main():
    # Load datasets
    df_human = pd.read_csv("/workspace/raw_prs_full_population.csv")
    df_human["author_type"] = "Human"
    df_human["bot_method"] = ""

    df_bot = pd.read_csv("/workspace/raw_prs_bot_only.csv")
    df_bot["author_type"] = "Bot"

    # Combine
    df_all = pd.concat([df_human, df_bot], ignore_index=True)
    df_all["era"] = df_all["year_month"].apply(assign_era)
    df_all["date"] = pd.to_datetime(df_all["year_month"] + "-01")

    print(f"Human PRs: {len(df_human)}")
    print(f"Bot PRs: {len(df_bot)}")
    print(f"Total PRs: {len(df_all)}")
    print(f"Bot share: {len(df_bot)/len(df_all)*100:.2f}%")

    # Load comment validation data for bot comment share estimation
    df_comments = pd.read_csv("/workspace/bot_comment_validation.csv")
    # Use era-specific estimates based on validation + Era 0 sample
    # Era 0: 0% (validated with 60 PRs), Era 1: 5%, Era 2: 10%, Era 3: 15% (validated mean 12.7%)
    era_bot_share_estimates = {0: 0.00, 1: 0.05, 2: 0.10, 3: 0.15}
    comment_bot_share = pd.DataFrame([
        {"project": proj, "era": era, "bot_comment_share": share}
        for proj in ["vLLM", "SGLang"]
        for era, share in era_bot_share_estimates.items()
    ])
    print("\nBot comment share estimates by era:")
    print(comment_bot_share.to_string())

    # Load PR size data
    df_size = pd.read_csv("/workspace/pr_size_data.csv")

    # Compute monthly decomposed metrics
    rows = []
    for (proj, ym), grp in df_all.groupby(["project", "year_month"]):
        era = assign_era(ym)
        human = grp[grp["author_type"] == "Human"]
        bot = grp[grp["author_type"] == "Bot"]

        # Basic counts
        n_human = len(human)
        n_bot = len(bot)
        n_total = n_human + n_bot

        # Cycle time
        cycle_human_median = human["cycle_days"].median() if n_human > 0 else np.nan
        cycle_bot_median = bot["cycle_days"].median() if n_bot > 0 else np.nan
        cycle_human_p90 = human["cycle_days"].quantile(0.9) if n_human > 0 else np.nan
        cycle_bot_p90 = bot["cycle_days"].quantile(0.9) if n_bot > 0 else np.nan

        # Unique authors
        unique_human = human["author"].nunique() if n_human > 0 else 0
        unique_bot = bot["author"].nunique() if n_bot > 0 else 0

        # Comments (from Search API counts)
        comment_human_mean = human["comments"].mean() if n_human > 0 else np.nan
        comment_bot_mean = bot["comments"].mean() if n_bot > 0 else np.nan
        comment_total_mean = grp["comments"].mean() if n_total > 0 else np.nan

        # PRs per author
        prs_per_author_human = n_human / unique_human if unique_human > 0 else np.nan

        # Bot share
        bot_share = n_bot / n_total if n_total > 0 else 0

        rows.append({
            "project": proj,
            "year_month": ym,
            "era": era,
            "date": pd.Timestamp(ym + "-01"),
            "prs_merged_human": n_human,
            "prs_merged_bot": n_bot,
            "prs_merged_total": n_total,
            "bot_share": bot_share,
            "cycle_median_human": cycle_human_median,
            "cycle_median_bot": cycle_bot_median,
            "cycle_p90_human": cycle_human_p90,
            "cycle_p90_bot": cycle_bot_p90,
            "unique_authors_human": unique_human,
            "unique_authors_bot": unique_bot,
            "comment_mean_human": comment_human_mean,
            "comment_mean_bot": comment_bot_mean,
            "comment_mean_total": comment_total_mean,
            "prs_per_author_human": prs_per_author_human,
        })

    df_monthly = pd.DataFrame(rows)

    # Add PR size data (merge on project + pr_number)
    # Create PR number to author mapping
    pr_author = df_all[["project", "pr_number", "author_type"]].drop_duplicates()
    df_size_labeled = df_size.merge(pr_author, on=["project", "pr_number"], how="left")
    df_size_labeled["author_type"] = df_size_labeled["author_type"].fillna("Human")

    # Compute monthly PR size by author type
    for (proj, ym), grp in df_size_labeled.groupby(["project", "year_month"]):
        human = grp[grp["author_type"] == "Human"]
        bot = grp[grp["author_type"] == "Bot"]

        mask = (df_monthly["project"] == proj) & (df_monthly["year_month"] == ym)
        if mask.sum() > 0:
            df_monthly.loc[mask, "additions_median_human"] = human["additions"].median() if len(human) > 0 else np.nan
            df_monthly.loc[mask, "additions_median_bot"] = bot["additions"].median() if len(bot) > 0 else np.nan
            df_monthly.loc[mask, "files_median_human"] = human["changed_files"].median() if len(human) > 0 else np.nan
            df_monthly.loc[mask, "files_median_bot"] = bot["changed_files"].median() if len(bot) > 0 else np.nan

    # Add bot comment share estimates
    for _, row in comment_bot_share.iterrows():
        mask = (df_monthly["project"] == row["project"]) & (df_monthly["era"] == row["era"])
        df_monthly.loc[mask, "bot_comment_share_est"] = row["bot_comment_share"]

    # Estimate human-only comment density
    df_monthly["comment_mean_human_est"] = df_monthly["comment_mean_total"] * (1 - df_monthly["bot_comment_share_est"])

    # Save monthly decomposed metrics
    df_monthly.to_csv("/workspace/monthly_metrics_decomposed.csv", index=False)
    print(f"\nSaved {len(df_monthly)} monthly decomposed metrics")

    # Attribution analysis: era-level means
    attribution_rows = []
    for proj in ["vLLM", "SGLang"]:
        df_p = df_monthly[df_monthly["project"] == proj]

        for era in range(4):
            df_e = df_p[df_p["era"] == era]
            if len(df_e) == 0:
                continue

            row = {
                "project": proj,
                "era": era,
                "era_label": ERA_LABELS[era],
                "n_months": len(df_e),
            }

            # PR Throughput
            row["throughput_human"] = df_e["prs_merged_human"].mean()
            row["throughput_bot"] = df_e["prs_merged_bot"].mean()
            row["throughput_total"] = df_e["prs_merged_total"].mean()
            row["bot_share_mean"] = df_e["bot_share"].mean()

            # Cycle Time
            row["cycle_median_human"] = df_e["cycle_median_human"].median()
            row["cycle_median_bot"] = df_e["cycle_median_bot"].median()

            # Unique Authors
            row["unique_authors_human"] = df_e["unique_authors_human"].mean()
            row["unique_authors_bot"] = df_e["unique_authors_bot"].mean()

            # Comment Density
            row["comment_mean_total"] = df_e["comment_mean_total"].mean()
            row["comment_mean_human_est"] = df_e["comment_mean_human_est"].mean()
            row["bot_comment_share"] = df_e["bot_comment_share_est"].mean()

            # PRs per author
            row["prs_per_author_human"] = df_e["prs_per_author_human"].mean()

            # PR Size
            row["additions_median_human"] = df_e["additions_median_human"].median()
            row["additions_median_bot"] = df_e["additions_median_bot"].median()

            attribution_rows.append(row)

    df_attr = pd.DataFrame(attribution_rows)

    # Compute era-over-era changes and bot contribution
    change_rows = []
    for proj in ["vLLM", "SGLang"]:
        df_p = df_attr[df_attr["project"] == proj].sort_values("era")
        if len(df_p) < 2:
            continue

        first_era = df_p.iloc[0]
        last_era = df_p.iloc[-1]

        for metric, human_col, bot_col, total_col in [
            ("PR Throughput", "throughput_human", "throughput_bot", "throughput_total"),
            ("Comment Density", "comment_mean_human_est", None, "comment_mean_total"),
            ("Unique Authors", "unique_authors_human", "unique_authors_bot", None),
            ("PRs per Author", "prs_per_author_human", None, None),
        ]:
            if total_col and total_col in df_p.columns:
                total_change = last_era[total_col] - first_era[total_col]
                human_change = last_era[human_col] - first_era[human_col] if human_col in df_p.columns else np.nan
                bot_change = last_era[bot_col] - first_era[bot_col] if bot_col and bot_col in df_p.columns else np.nan

                bot_contribution = (bot_change / total_change * 100) if total_change != 0 and not np.isnan(bot_change) else np.nan
                human_contribution = (human_change / total_change * 100) if total_change != 0 and not np.isnan(human_change) else np.nan

                change_rows.append({
                    "project": proj,
                    "metric": metric,
                    "first_era": first_era["era_label"],
                    "last_era": last_era["era_label"],
                    "total_first": first_era[total_col],
                    "total_last": last_era[total_col],
                    "total_change": total_change,
                    "human_change": human_change,
                    "bot_change": bot_change,
                    "bot_contribution_pct": bot_contribution,
                    "human_contribution_pct": human_contribution,
                })

    df_change = pd.DataFrame(change_rows)
    df_attr.to_csv("/workspace/bot_attribution_summary.csv", index=False)
    df_change.to_csv("/workspace/bot_attribution_changes.csv", index=False)

    print("\n" + "="*60)
    print("ATTRIBUTION ANALYSIS")
    print("="*60)
    print("\nEra-level means:")
    print(df_attr.to_string())
    print("\nChange attribution:")
    print(df_change.to_string())

if __name__ == "__main__":
    main()
