#!/usr/bin/env python3
"""
Collect full-population PR data for vLLM and SGLang via GitHub Search API.

Fetches ALL merged PRs per month (not a sample) for:
  - Cycle time (created_at -> closed_at)
  - Contributor breadth (unique authors)
  - Comment density (issue comments per PR)
  - Contributor diversity (new vs returning authors)

Handles Search API 1000-result cap by splitting high-volume months into
half-month windows. Rate limit: 10 req/min unauthenticated (7s sleep).

Output: /workspace/raw_prs_full_population.csv
"""
import requests, time, math, sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

HEADERS = {"Accept": "application/vnd.github+json"}
OUT_CSV = "/workspace/raw_prs_full_population.csv"
CHECKPOINT_CSV = "/workspace/raw_prs_checkpoint.csv"

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
                # Validation failed (e.g., page beyond 1000)
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
    # First, get total count
    result = gh_search_page(q, per_page=1, page=1)
    total = result.get("total_count", 0)
    if total == 0:
        return []
    
    # If total > 1000, we need to split (handled by caller)
    if total > 1000:
        return None  # Signal to caller to split
    
    # Fetch all pages
    all_items = []
    n_pages = math.ceil(total / 100)
    for page in range(1, n_pages + 1):
        result = gh_search_page(q, per_page=100, page=page)
        items = result.get("items", [])
        all_items.extend(items)
        if page < n_pages:
            time.sleep(7)  # Rate limit: 10 req/min
    
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

def extract_pr_data(items, project, year_month):
    """Extract relevant fields from Search API items."""
    rows = []
    for item in items:
        user = item.get("user", {})
        login = user.get("login", "")
        # Filter bots
        if "[bot]" in login.lower() or "bot" in login.lower():
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
                        # Still too many - split further (shouldn't happen)
                        print(f"WARN: {label} half-month still >1000", flush=True)
                        half_items = []
                    items.extend(half_items)
                    time.sleep(7)
            
            rows = extract_pr_data(items, proj_name, label)
            all_rows.extend(rows)
            print(f"n={len(rows)}", flush=True)
            
            # Checkpoint every 10 months
            if (i + 1) % 10 == 0:
                pd.DataFrame(all_rows).to_csv(CHECKPOINT_CSV, index=False)
                print(f"  [checkpoint: {len(all_rows)} rows]", flush=True)
            
            time.sleep(7)  # Rate limit between months
    
    df = pd.DataFrame(all_rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"\n{'='*60}")
    print(f"DONE — {len(df)} rows saved to {OUT_CSV}")
    print(f"{'='*60}")
    print(df.groupby("project").size())

if __name__ == "__main__":
    main()
