#!/usr/bin/env python3
"""
Sample PRs stratified by project × era and fetch individual comments
to estimate bot comment share.

Output: /workspace/bot_comment_sample.csv
"""
import requests, time, sys
import pandas as pd
import numpy as np
from datetime import datetime

HEADERS = {"Accept": "application/vnd.github+json"}
OUT_CSV = "/workspace/bot_comment_sample.csv"

# Era definitions (same as main analysis)
def assign_era(ym):
    dt = pd.Timestamp(ym)
    if dt < pd.Timestamp("2023-10"): return 0
    if dt < pd.Timestamp("2024-06"): return 1
    if dt < pd.Timestamp("2025-01"): return 2
    return 3

def fetch_pr_comments(repo, pr_number, retries=5):
    """Fetch all issue comments for a PR."""
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    all_comments = []
    page = 1
    while True:
        for attempt in range(retries):
            try:
                r = requests.get(url, params={"per_page": 100, "page": page},
                                 headers=HEADERS, timeout=30)
                if r.status_code == 200:
                    comments = r.json()
                    all_comments.extend(comments)
                    if len(comments) < 100:
                        return all_comments
                    page += 1
                    time.sleep(7)
                    break
                elif r.status_code in (403, 429):
                    reset = int(r.headers.get("X-RateLimit-Reset", time.time() + 65))
                    wait = max(reset - time.time(), 15)
                    print(f" [rl:{wait:.0f}s]", end="", flush=True)
                    time.sleep(wait)
                else:
                    time.sleep(5)
            except Exception as e:
                print(f" [err:{e}]", end="", flush=True)
                time.sleep(8)
        else:
            return all_comments  # Return what we have after retries exhausted
    return all_comments

def main():
    # Load existing human-only PR data
    df = pd.read_csv("/workspace/raw_prs_full_population.csv")
    df["era"] = df["year_month"].apply(assign_era)

    # Stratified sampling: 50 PRs per project × era
    SAMPLE_SIZE = 50
    samples = []

    for project in ["vLLM", "SGLang"]:
        repo = "vllm-project/vllm" if project == "vLLM" else "sgl-project/sglang"
        df_p = df[df["project"] == project]

        for era in range(4):
            df_e = df_p[df_p["era"] == era]
            n_available = len(df_e)
            n_sample = min(SAMPLE_SIZE, n_available)

            if n_sample == 0:
                print(f"  {project} Era {era}: no PRs available, skipping")
                continue

            sampled = df_e.sample(n=n_sample, random_state=42)
            print(f"  {project} Era {era}: {n_available} PRs available, sampled {n_sample}")

            for _, row in sampled.iterrows():
                samples.append({
                    "project": project,
                    "repo": repo,
                    "pr_number": row["pr_number"],
                    "year_month": row["year_month"],
                    "era": era,
                    "total_comments_search_api": row["comments"],
                })

    print(f"\nTotal PRs to fetch comments for: {len(samples)}")

    # Fetch comments for each sampled PR
    results = []
    for i, s in enumerate(samples):
        print(f"  [{i+1}/{len(samples)}] {s['project']} PR#{s['pr_number']}", end=" ... ", flush=True)

        comments = fetch_pr_comments(s["repo"], s["pr_number"])

        bot_count = 0
        human_count = 0
        bot_logins = set()

        for c in comments:
            user = c.get("user", {})
            utype = user.get("type", "")
            login = user.get("login", "")

            if utype == "Bot":
                bot_count += 1
                bot_logins.add(login)
            else:
                human_count += 1

        total = bot_count + human_count
        bot_share = bot_count / total if total > 0 else 0

        results.append({
            "project": s["project"],
            "pr_number": s["pr_number"],
            "year_month": s["year_month"],
            "era": s["era"],
            "total_comments_search_api": s["total_comments_search_api"],
            "total_comments_fetched": total,
            "bot_comments": bot_count,
            "human_comments": human_count,
            "bot_share": bot_share,
            "bot_logins": ";".join(sorted(bot_logins)),
        })

        print(f"{total} comments ({bot_count} bot, {human_count} human)", flush=True)

        if i < len(samples) - 1:
            time.sleep(7)

    df_out = pd.DataFrame(results)
    df_out.to_csv(OUT_CSV, index=False)

    print(f"\n{'='*60}")
    print(f"  Saved {len(df_out)} sampled PRs to {OUT_CSV}")
    print(f"{'='*60}")

    # Summary by project × era
    print("\nBot comment share by project × era:")
    summary = df_out.groupby(["project", "era"]).agg(
        n_prs=("pr_number", "count"),
        mean_bot_share=("bot_share", "mean"),
        total_bot=("bot_comments", "sum"),
        total_human=("human_comments", "sum"),
        total_all=("total_comments_fetched", "sum"),
    )
    summary["overall_bot_share"] = summary["total_bot"] / summary["total_all"]
    print(summary.to_string())

if __name__ == "__main__":
    main()
