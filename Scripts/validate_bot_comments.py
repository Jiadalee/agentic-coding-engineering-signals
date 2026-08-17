#!/usr/bin/env python3
"""
Validate bot comment share on a small targeted sample.
Fetch comments for 10 recent PRs (5 from each project) to verify
the estimated bot comment share.

Output: /workspace/bot_comment_validation.csv
"""
import requests, time, sys
import pandas as pd
import numpy as np

HEADERS = {"Accept": "application/vnd.github+json"}
OUT_CSV = "/workspace/bot_comment_validation.csv"

def fetch_pr_comments(repo, pr_number, retries=3):
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
                    time.sleep(8)
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
            return all_comments
    return all_comments

def main():
    # Load existing data
    df = pd.read_csv("/workspace/raw_prs_full_population.csv")

    # Sample 5 recent PRs with high comment counts from each project
    samples = []
    for project in ["vLLM", "SGLang"]:
        repo = "vllm-project/vllm" if project == "vLLM" else "sgl-project/sglang"
        df_p = df[(df["project"] == project) & (df["year_month"] >= "2025-01")]
        # Sample PRs with high comment counts (more likely to have bot activity)
        df_high = df_p[df_p["comments"] >= 5].sample(n=min(5, len(df_p[df_p["comments"] >= 5])), random_state=42)
        for _, row in df_high.iterrows():
            samples.append({
                "project": project,
                "repo": repo,
                "pr_number": row["pr_number"],
                "year_month": row["year_month"],
                "comments_search_api": row["comments"],
            })

    print(f"Validating bot comment share on {len(samples)} recent PRs")

    results = []
    for i, s in enumerate(samples):
        print(f"  [{i+1}/{len(samples)}] {s['project']} PR#{s['pr_number']} ({s['year_month']}, {s['comments_search_api']} comments)", end=" ... ", flush=True)

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
            "comments_search_api": s["comments_search_api"],
            "comments_fetched": total,
            "bot_comments": bot_count,
            "human_comments": human_count,
            "bot_share": bot_share,
            "bot_logins": ";".join(sorted(bot_logins)),
        })

        print(f"{total} fetched ({bot_count} bot, {human_count} human, {bot_share*100:.0f}% bot)", flush=True)

        if i < len(samples) - 1:
            time.sleep(8)

    df_out = pd.DataFrame(results)
    df_out.to_csv(OUT_CSV, index=False)

    print(f"\n{'='*60}")
    print(f"  Saved {len(df_out)} validation results to {OUT_CSV}")
    print(f"{'='*60}")

    print("\nValidation summary:")
    print(df_out[["project", "pr_number", "comments_search_api", "comments_fetched", "bot_comments", "bot_share"]].to_string())

    print(f"\nMean bot share: {df_out['bot_share'].mean()*100:.1f}%")
    print(f"Median bot share: {df_out['bot_share'].median()*100:.1f}%")

if __name__ == "__main__":
    main()
