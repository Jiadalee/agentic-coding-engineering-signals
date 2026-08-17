#!/usr/bin/env python3
"""
Collect bot-authored merged PRs for vLLM and SGLang via GitHub Search API.

Two-tier bot identification:
1. GitHub account-type metadata (user.type == "Bot")
2. Username-based matching for common bot patterns

Output: /workspace/raw_prs_bot_only.csv
"""
import requests, time, math, sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

HEADERS = {"Accept": "application/vnd.github+json"}
OUT_CSV = "/workspace/raw_prs_bot_only.csv"

# Known bot name patterns (case-insensitive)
BOT_PATTERNS = [
    "[bot]", "dependabot", "renovate", "github-actions", "mergify",
    "pre-commit-ci", "codecov", "mintlify", "stale", "semantic-release",
    "greenkeeper", "snyk-bot", "pyup-bot", "imgbot", "allcontributors",
    "welcome", "first-interaction", "labeler", "auto-assign",
]

def is_bot_username(login):
    """Check if a username matches known bot patterns."""
    login_lower = login.lower()
    for pattern in BOT_PATTERNS:
        if pattern in login_lower:
            return True
    return False

def gh_search_page(q, per_page=100, page=1, retries=8):
    """Fetch one page of Search API results with retry + rate-limit handling."""
    url = "https://api.github.com/search/issues"
    for attempt in range(retries):
        try:
            r = requests.get(url, params={"q": q, "per_page": per_page, "page": page},
                             headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (403, 429):
                reset = int(r.headers.get("X-RateLimit-Reset", time.time() + 65))
                wait = max(reset - time.time(), 15)
                print(f" [rl:{wait:.0f}s]", end="", flush=True)
                time.sleep(wait)
            elif r.status_code == 422:
                return {"items": [], "total_count": 0}
            else:
                time.sleep(5)
        except Exception as e:
            print(f" [err:{e}]", end="", flush=True)
            time.sleep(8)
    return {"items": [], "total_count": 0}

def fetch_all_merged_prs(repo, d0, d1):
    """Fetch ALL merged PRs for a date range, handling pagination."""
    q = f"repo:{repo} is:pr is:merged merged:{d0}..{d1}"
    result = gh_search_page(q, per_page=1, page=1)
    total = result.get("total_count", 0)
    if total == 0:
        return []
    if total > 1000:
        return None  # Signal to caller to split

    all_items = []
    n_pages = math.ceil(total / 100)
    for page in range(1, n_pages + 1):
        result = gh_search_page(q, per_page=100, page=page)
        items = result.get("items", [])
        all_items.extend(items)
        if page < n_pages:
            time.sleep(7)
    return all_items

def month_ranges(start_ym, end_ym):
    """Generate (year, month, start_date, end_date) tuples."""
    cur = datetime(start_ym[0], start_ym[1], 1)
    end = datetime(end_ym[0], end_ym[1], 1)
    while cur <= end:
        nxt = cur + relativedelta(months=1)
        yield (cur.year, cur.month,
               cur.strftime("%Y-%m-%d"),
               (nxt - timedelta(days=1)).strftime("%Y-%m-%d"))
        cur = nxt

def split_month(d0, d1):
    """Split a month into two halves."""
    start = datetime.strptime(d0, "%Y-%m-%d")
    end = datetime.strptime(d1, "%Y-%m-%d")
    mid = start + (end - start) / 2
    return [(d0, mid.strftime("%Y-%m-%d")),
            ((mid + timedelta(days=1)).strftime("%Y-%m-%d"), d1)]

def extract_bot_prs(items, project, year_month):
    """Extract bot-authored PRs from Search API items."""
    rows = []
    for item in items:
        user = item.get("user", {})
        login = user.get("login", "")
        user_type = user.get("type", "")

        # Two-tier bot identification
        is_bot = False
        bot_method = ""
        if user_type == "Bot":
            is_bot = True
            bot_method = "account_type"
        elif is_bot_username(login):
            is_bot = True
            bot_method = "username_pattern"

        if not is_bot:
            continue

        created = item.get("created_at", "")
        closed = item.get("closed_at", "")
        comments = item.get("comments", 0)
        pr_number = item.get("number", 0)
        title = item.get("title", "")

        # Compute cycle time
        if created and closed:
            try:
                ct = (datetime.fromisoformat(closed.replace("Z", "+00:00")) -
                      datetime.fromisoformat(created.replace("Z", "+00:00"))).total_seconds() / 86400
            except:
                ct = np.nan
        else:
            ct = np.nan

        rows.append({
            "project": project,
            "year_month": year_month,
            "pr_number": pr_number,
            "author": login,
            "author_type": user_type,
            "bot_method": bot_method,
            "created_at": created,
            "closed_at": closed,
            "cycle_days": ct,
            "comments": comments,
            "title": title,
        })
    return rows

def main():
    projects = {
        "vLLM":   ("vllm-project/vllm",  (2023, 2), (2026, 6)),
        "SGLang": ("sgl-project/sglang", (2024, 1), (2026, 6)),
    }

    all_rows = []

    for proj_name, (repo, start, end) in projects.items():
        months = list(month_ranges(start, end))
        print(f"\n{'='*60}")
        print(f"  {proj_name} — {len(months)} months")
        print(f"{'='*60}", flush=True)

        proj_bot_count = 0
        proj_total_count = 0

        for i, (yr, mo, d0, d1) in enumerate(months):
            label = f"{yr}-{mo:02d}"
            print(f"  [{i+1:02d}/{len(months)}] {label}", end=" ... ", flush=True)

            items = fetch_all_merged_prs(repo, d0, d1)

            if items is None:
                # Need to split month
                print("SPLIT", end=" ", flush=True)
                halves = split_month(d0, d1)
                items = []
                for h0, h1 in halves:
                    half_items = fetch_all_merged_prs(repo, h0, h1)
                    if half_items is None:
                        # Split further into quarters
                        for q0, q1 in split_month(h0, h1):
                            quarter_items = fetch_all_merged_prs(repo, q0, q1)
                            if quarter_items:
                                items.extend(quarter_items)
                            time.sleep(7)
                    else:
                        items.extend(half_items)
                    time.sleep(7)

            bot_rows = extract_bot_prs(items, proj_name, label)
            all_rows.extend(bot_rows)
            proj_bot_count += len(bot_rows)
            proj_total_count += len(items)
            print(f"{len(items)} PRs, {len(bot_rows)} bot", flush=True)

            if i < len(months) - 1:
                time.sleep(7)

        print(f"\n  {proj_name} total: {proj_total_count} PRs, {proj_bot_count} bot ({proj_bot_count/max(proj_total_count,1)*100:.1f}%)")

    df = pd.DataFrame(all_rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"\n{'='*60}")
    print(f"  Saved {len(df)} bot PRs to {OUT_CSV}")
    print(f"{'='*60}")

    # Summary by project
    if len(df) > 0:
        print("\nBot PRs by project:")
        print(df.groupby("project").size())
        print("\nBot PRs by author:")
        print(df.groupby(["project", "author"]).size().sort_values(ascending=False).head(20))
        print("\nBot identification method:")
        print(df.groupby("bot_method").size())

if __name__ == "__main__":
    main()
