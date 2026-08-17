#!/usr/bin/env python3
"""
Generate all figures (v6) for the revised manuscript with bot/human decomposition.
- 500 dpi, enlarged fonts
- No suptitles (captions are in the manuscript, not baked into images)
- Era labels placed above plot area (no overlap with data)
- SGLang panels show empty Era 0 region for visual consistency
- Figures 1-7: Updated with bot/human decomposition where relevant
- Figure 8: NEW — Bot PR prevalence across eras
- Figure 9: NEW — Human vs. bot metric comparison
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
from matplotlib.colors import TwoSlopeNorm
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

# ── Global style: enlarged fonts for 500 dpi ─────────────────────────────────
FS_TITLE   = 18
FS_LABEL   = 14
FS_TICK    = 12
FS_LEGEND  = 12
FS_ANNOT   = 11
FS_ERA     = 10

matplotlib.rcParams.update({
    "font.family":        ["Liberation Sans", "Arimo", "DejaVu Sans"],
    "svg.fonttype":       "none",
    "figure.dpi":         150,
    "savefig.dpi":        500,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.alpha":         0.25,
    "grid.linestyle":     "--",
    "axes.labelsize":     FS_LABEL,
    "xtick.labelsize":    FS_TICK,
    "ytick.labelsize":    FS_TICK,
    "legend.fontsize":    FS_LEGEND,
    "axes.titlesize":     FS_TITLE,
})

COLORS = {"vLLM": "#0279EE", "SGLang": "#FF9400"}
COLORS_BOT = {"vLLM": "#0279EE", "SGLang": "#FF9400"}
COLORS_HUMAN = {"vLLM": "#0279EE", "SGLang": "#FF9400"}

ERA_DEFS = [
    ("2023-02", "2023-09", "#BBBBBB", "Era 0\nPre-Agentic\nBaseline"),
    ("2023-10", "2024-05", "#C8C800", "Era 1\nEarly AI\nCoding Tools"),
    ("2024-06", "2024-12", "#E060C0", "Era 2\nVibe Coding\nMainstream"),
    ("2025-01", "2026-06", "#4A8000", "Era 3\nAgentic Coding\nEmergence"),
]
ERA_ALPHA = 0.15
ERA_COLORS_POINT = ["#888888", "#B8B800", "#C040A0", "#3A6800"]
ERA_LABELS_POINT = ["Era 0: Pre-Agentic Baseline", "Era 1: Early AI Coding Tools",
                    "Era 2: Vibe Coding Mainstream", "Era 3: Agentic Coding Emergence"]

KEY_EVENTS = [
    ("2023-10-01", "Copilot GA",      0.88),
    ("2024-01-08", "SGLang Launches", 0.72),
    ("2024-03-12", "Devin Launches",  0.56),
    ("2025-02-24", "Claude Code GA",  0.88),
    ("2025-06-01", "Cursor Agent",    0.72),
]

def assign_era(ym):
    dt = pd.Timestamp(ym)
    if dt < pd.Timestamp("2023-10"): return 0
    if dt < pd.Timestamp("2024-06"): return 1
    if dt < pd.Timestamp("2025-01"): return 2
    return 3

def add_era_shading(ax, xmin, xmax, show_labels=True):
    """Add era shading bands and place labels above the plot area."""
    for era_start, era_end, color, label in ERA_DEFS:
        s = max(pd.Timestamp(era_start), xmin)
        e = min(pd.Timestamp(era_end) + pd.offsets.MonthEnd(0), xmax)
        if s >= e: continue
        ax.axvspan(s, e, alpha=ERA_ALPHA, color=color, zorder=0)
        if show_labels:
            mid = s + (e - s) / 2
            xlim = ax.get_xlim()
            mid_num = mdates.date2num(mid)
            x_frac = (mid_num - xlim[0]) / (xlim[1] - xlim[0])
            ax.text(x_frac, 1.08, label, transform=ax.transAxes,
                    ha="center", va="bottom", fontsize=FS_ERA-1, color="#555",
                    linespacing=1.1)

def fmt_xaxis(ax):
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

def add_key_events(ax, ymin, ymax):
    xlim = ax.get_xlim()
    for date_str, label, y_frac in KEY_EVENTS:
        d = pd.Timestamp(date_str)
        d_num = mdates.date2num(d)
        if d_num < xlim[0] or d_num > xlim[1]:
            continue
        ax.axvline(d, color="#999", lw=0.8, ls=":", zorder=1)
        ax.text(d_num, y_frac, label, transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=FS_ANNOT-2, color="#777",
                rotation=90, rotation_mode="anchor")

# ═══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════════
print("Loading data...")

# Original metrics (human-only)
df = pd.read_csv("/workspace/monthly_metrics_full.csv")
df["date"] = pd.to_datetime(df["date"])

# Decomposed metrics (human + bot)
df_dec = pd.read_csv("/workspace/monthly_metrics_decomposed.csv")
df_dec["date"] = pd.to_datetime(df_dec["date"])

vllm = df[df["project"] == "vLLM"].sort_values("date").reset_index(drop=True)
sglang = df[df["project"] == "SGLang"].sort_values("date").reset_index(drop=True)

vllm_dec = df_dec[df_dec["project"] == "vLLM"].sort_values("date").reset_index(drop=True)
sglang_dec = df_dec[df_dec["project"] == "SGLang"].sort_values("date").reset_index(drop=True)

print(f"vLLM: {len(vllm)} months, SGLang: {len(sglang)} months")
print(f"vLLM decomposed: {len(vllm_dec)} months, SGLang decomposed: {len(sglang_dec)} months")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 1 — PR Throughput (updated with bot decomposition)
# ═══════════════════════════════════════════════════════════════════════════════
print("Generating Figure 1...")
fig, ax = plt.subplots(figsize=(14, 7))

for proj, df_p, df_d in [("vLLM", vllm, vllm_dec), ("SGLang", sglang, sglang_dec)]:
    col = COLORS[proj]
    ax.plot(df_p["date"], df_p["prs_merged"], color=col, lw=2.5, marker="o", ms=5,
            label=f"{proj} merged (human)", zorder=5)
    ax.plot(df_p["date"], df_p["prs_opened"], color=col, lw=1.5, ls="--", alpha=0.6,
            label=f"{proj} opened", zorder=4)
    # Add bot PRs if available
    if "prs_merged_bot" in df_d.columns:
        ax.plot(df_d["date"], df_d["prs_merged_bot"], color=col, lw=1.5, ls=":",
                marker="s", ms=3, alpha=0.7, label=f"{proj} merged (bot)", zorder=4)

ax.set_ylabel("PRs / Month", fontsize=FS_LABEL)
ax.set_xlabel("Month", fontsize=FS_LABEL)
ax.legend(fontsize=FS_LEGEND, loc="upper left", framealpha=0.9)
fmt_xaxis(ax)
add_era_shading(ax, df["date"].min(), df["date"].max())
add_key_events(ax, 0, ax.get_ylim()[1])

plt.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig("/mnt/results/fig1_pr_throughput_timeseries_v6.png",
            dpi=500, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✓ Figure 1 saved")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 2 — PR Cycle Time (unchanged, but with bot median overlay)
# ═══════════════════════════════════════════════════════════════════════════════
print("Generating Figure 2...")
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

for ax, (proj, df_p, df_d) in zip(axes, [("vLLM", vllm, vllm_dec), ("SGLang", sglang, sglang_dec)]):
    col = COLORS[proj]
    dates = df_p["date"].values
    med = df_p["cycle_median_days"].values
    p90 = df_p["cycle_p90_days"].values

    ax.fill_between(dates, med, p90, alpha=0.20, color=col, label="Median–P90 band")
    ax.plot(dates, med, color=col, lw=2.5, marker="o", ms=5, label="Median (human)", zorder=5)
    ax.plot(dates, p90, color=col, lw=1.8, ls="--", marker="s", ms=4, label="P90 (human)", zorder=4)

    # Bot cycle time if available
    if "cycle_median_bot" in df_d.columns:
        bot_med = df_d["cycle_median_bot"].values
        valid = ~np.isnan(bot_med)
        if valid.sum() > 0:
            ax.plot(df_d["date"].values[valid], bot_med[valid], color=col, lw=1.5, ls=":",
                    marker="^", ms=4, alpha=0.7, label="Median (bot)", zorder=4)

    # Era means
    for era_id in range(4):
        mask = df_p["era"].values == era_id
        if mask.sum() > 0:
            era_mean = np.nanmean(med[mask])
            era_dates = dates[mask]
            ax.axhline(era_mean, color=col, lw=1.2, ls="-.", alpha=0.5,
                       xmin=(era_dates.min() - dates.min()) / (dates.max() - dates.min()),
                       xmax=(era_dates.max() - dates.min()) / (dates.max() - dates.min()))

    ax.set_title(proj, fontsize=FS_TITLE, fontweight="bold", color=col)
    ax.set_xlabel("Month", fontsize=FS_LABEL)
    ax.set_ylabel("Cycle Time (days)", fontsize=FS_LABEL)
    ax.legend(fontsize=FS_LEGEND, loc="upper left", framealpha=0.9)
    fmt_xaxis(ax)
    x_min = df["date"].min() if proj == "SGLang" else df_p["date"].min()
    ax.set_xlim(x_min, df_p["date"].max())
    add_era_shading(ax, x_min, df_p["date"].max())

plt.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig("/mnt/results/fig2_pr_cycle_time_comparison_v6.png",
            dpi=500, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✓ Figure 2 saved")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 3 — Contributor Breadth (unchanged)
# ═══════════════════════════════════════════════════════════════════════════════
print("Generating Figure 3...")
fig, axes = plt.subplots(1, 2, figsize=(16, 7.5))

for ax, (proj, df_p) in zip(axes, [("vLLM", vllm), ("SGLang", sglang)]):
    col = COLORS[proj]
    x_num = df_p["month_num"].values
    y = df_p["unique_contributors"].values
    dates = df_p["date"].values

    for era_id, era_col in enumerate(ERA_COLORS_POINT):
        mask = df_p["era"].values == era_id
        if mask.sum() > 0:
            ax.scatter(dates[mask], y[mask], color=era_col, s=80, zorder=5,
                       label=ERA_LABELS_POINT[era_id],
                       edgecolors="white", linewidths=0.8)

    roll = pd.Series(y).rolling(3, center=True, min_periods=1).mean()
    ax.plot(dates, roll, color=col, lw=2.5, alpha=0.7, zorder=4, label="3-mo rolling avg")

    slope, intercept, r, p_val, se = stats.linregress(x_num, y)
    x_line = np.linspace(x_num.min(), x_num.max(), 100)
    y_line = slope * x_line + intercept
    n = len(x_num)
    x_mean = np.mean(x_num)
    sxx = np.sum((x_num - x_mean)**2)
    s_err = np.sqrt(np.sum((y - (slope*x_num + intercept))**2) / (n - 2))
    ci = 1.96 * s_err * np.sqrt(1/n + (x_line - x_mean)**2 / sxx)

    global_min_date = df["date"].min()
    date_line = pd.to_datetime(global_min_date) + pd.to_timedelta(x_line * 30.44, unit="D")

    ci_lower = np.maximum(y_line - ci, 0)
    ax.fill_between(date_line, ci_lower, y_line + ci, alpha=0.15, color=col,
                    label="95% CI", zorder=3)
    ax.plot(date_line, y_line, color=col, lw=2.2, ls="-.",
            label=f"OLS: +{slope:.1f}/mo  r²={r**2:.2f}", zorder=6)

    ax.set_title(proj, fontsize=FS_TITLE, fontweight="bold", color=col)
    ax.set_xlabel("Month", fontsize=FS_LABEL)
    ax.set_ylabel("Unique Authors / Month", fontsize=FS_LABEL)
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=FS_LEGEND-1, loc="upper left", framealpha=0.9)
    fmt_xaxis(ax)
    x_min = df["date"].min() if proj == "SGLang" else df_p["date"].min()
    x_max = df_p["date"].max() + pd.Timedelta(days=45)
    ax.set_xlim(x_min, x_max)
    add_era_shading(ax, x_min, df_p["date"].max())

plt.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig("/mnt/results/fig3_contributor_breadth_scatter_regression_v6.png",
            dpi=500, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✓ Figure 3 saved")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 4 — Multi-metric Heatmap (unchanged)
# ═══════════════════════════════════════════════════════════════════════════════
print("Generating Figure 4...")

METRICS_HM = [
    ("prs_merged",          "PRs Merged / Month"),
    ("prs_opened",          "PRs Opened / Month"),
    ("merge_rate",          "Monthly Merge Rate"),
    ("cycle_p90_days",      "Cycle Time P90 (days) ↓"),
    ("unique_contributors", "Unique Authors / Month"),
    ("comment_mean",        "Avg Comments / PR"),
]

fig, axes = plt.subplots(1, 2, figsize=(19, 7.5))

for ax, (proj, df_p) in zip(axes, [("vLLM", vllm), ("SGLang", sglang)]):
    months = df_p["year_month"].values
    n_metrics = len(METRICS_HM)
    n_months = len(months)

    z_matrix = np.zeros((n_metrics, n_months))
    for i, (col_name, _) in enumerate(METRICS_HM):
        vals = df_p[col_name].values.astype(float)
        if col_name == "cycle_p90_days":
            vals = -vals
        mean, std = np.nanmean(vals), np.nanstd(vals)
        if std > 0:
            z_matrix[i] = (vals - mean) / std
        else:
            z_matrix[i] = 0

    im = ax.imshow(z_matrix, aspect="auto", cmap="RdYlGn", vmin=-2, vmax=2,
                   interpolation="nearest")

    tick_step = max(1, n_months // 8)
    ax.set_xticks(range(0, n_months, tick_step))
    ax.set_xticklabels([months[i] for i in range(0, n_months, tick_step)],
                       rotation=45, ha="right", fontsize=FS_TICK-1)

    ax.set_yticks(range(n_metrics))
    ax.set_yticklabels([label for _, label in METRICS_HM], fontsize=FS_TICK)

    for boundary, color in [("2023-10", "#B8B800"), ("2024-06", "#C040A0"), ("2025-01", "#3A6800")]:
        idx = np.where(months == boundary)[0]
        if len(idx) > 0:
            ax.axvline(idx[0] - 0.5, color=color, lw=2, ls="--", alpha=0.7)

    ax.set_title(proj, fontsize=FS_TITLE, fontweight="bold", color=COLORS[proj])
    ax.set_xlabel("Month", fontsize=FS_LABEL)

cbar_ax = fig.add_axes([0.15, 0.02, 0.7, 0.03])
fig.colorbar(im, cax=cbar_ax, orientation="horizontal", label="Z-score")
plt.tight_layout(rect=[0, 0.08, 1, 0.90])
fig.savefig("/mnt/results/fig4_metrics_heatmap_v6.png",
            dpi=500, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✓ Figure 4 saved")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 5 — PR Comment Density (updated with human-only estimate)
# ═══════════════════════════════════════════════════════════════════════════════
print("Generating Figure 5...")
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

for ax, (proj, df_p, df_d) in zip(axes, [("vLLM", vllm, vllm_dec), ("SGLang", sglang, sglang_dec)]):
    col = COLORS[proj]
    dates = df_p["date"].values
    vals = df_p["comment_mean"].values

    ax.plot(dates, vals, color=col, lw=1.5, marker="o", ms=3, alpha=0.5, zorder=3)

    roll = pd.Series(vals).rolling(3, center=True, min_periods=1).mean()
    ax.plot(dates, roll, color=col, lw=2.5, label="3-mo rolling avg (total)", zorder=5)

    # Human-only comment density estimate
    if "comment_mean_human_est" in df_d.columns:
        human_est = df_d["comment_mean_human_est"].values
        valid = ~np.isnan(human_est)
        if valid.sum() > 0:
            roll_human = pd.Series(human_est).rolling(3, center=True, min_periods=1).mean()
            ax.plot(df_d["date"].values, roll_human, color=col, lw=2.0, ls="--",
                    alpha=0.8, label="3-mo rolling avg (human est.)", zorder=4)

    # Era means
    for era_id in range(4):
        mask = df_p["era"].values == era_id
        if mask.sum() > 0:
            era_mean = np.nanmean(vals[mask])
            era_dates = dates[mask]
            ax.axhline(era_mean, color=col, lw=1.5, ls="-.", alpha=0.6,
                       xmin=(era_dates.min() - dates.min()) / (dates.max() - dates.min()),
                       xmax=(era_dates.max() - dates.min()) / (dates.max() - dates.min()),
                       label=f"Era {era_id} mean: {era_mean:.1f}")

    ax.set_title(proj, fontsize=FS_TITLE, fontweight="bold", color=col)
    ax.set_xlabel("Month", fontsize=FS_LABEL)
    ax.set_ylabel("Mean Comments / PR", fontsize=FS_LABEL)
    ax.legend(fontsize=FS_LEGEND-1, loc="upper left", framealpha=0.9)
    fmt_xaxis(ax)
    x_min = df["date"].min() if proj == "SGLang" else df_p["date"].min()
    ax.set_xlim(x_min, df_p["date"].max())
    add_era_shading(ax, x_min, df_p["date"].max())

plt.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig("/mnt/results/fig5_pr_comment_density_v6.png",
            dpi=500, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✓ Figure 5 saved")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 6 — Contributor Diversity (unchanged)
# ═══════════════════════════════════════════════════════════════════════════════
print("Generating Figure 6...")
fig, axes = plt.subplots(1, 2, figsize=(16, 7.5))

for ax, (proj, df_p) in zip(axes, [("vLLM", vllm), ("SGLang", sglang)]):
    col = COLORS[proj]
    dates = df_p["date"].values
    new_a = df_p["new_authors"].values
    ret_a = df_p["returning_authors"].values
    new_r = df_p["new_ratio"].values

    ax.stackplot(dates, ret_a, new_a,
                 labels=["Returning authors", "New authors"],
                 colors=[col, "#FFD580" if proj == "SGLang" else "#7EC8F7"],
                 alpha=0.75, zorder=2)

    ax2 = ax.twinx()
    ax2.plot(dates, new_r * 100, color="#CC0000", lw=2.2, ls="-",
             marker="s", ms=4, label="New author ratio (%)", zorder=5)
    ax2.set_ylabel("New Author Ratio (%)", fontsize=FS_LABEL, color="#CC0000")
    ax2.tick_params(axis="y", labelcolor="#CC0000", labelsize=FS_TICK)
    ax2.set_ylim(0, 105)

    ax.set_title(proj, fontsize=FS_TITLE, fontweight="bold", color=col)
    ax.set_xlabel("Month", fontsize=FS_LABEL)
    ax.set_ylabel("Authors / Month", fontsize=FS_LABEL)
    ax.autoscale(axis="y")
    ylo, yhi = ax.get_ylim(); ax.set_ylim(max(ylo, 0), yhi * 1.25)
    x_min = df["date"].min() if proj == "SGLang" else df_p["date"].min()
    ax.set_xlim(x_min, df_p["date"].max())
    add_era_shading(ax, x_min, df_p["date"].max(), show_labels=True)

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2,
              fontsize=FS_LEGEND-1, loc="upper right", framealpha=0.9)
    fmt_xaxis(ax)

plt.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig("/mnt/results/fig6_contributor_diversity_v6.png",
            dpi=500, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✓ Figure 6 saved")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 7 — PR-Size Analysis (unchanged)
# ═══════════════════════════════════════════════════════════════════════════════
print("Generating Figure 7...")
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

for ax, (proj, df_p) in zip(axes[0], [("vLLM", vllm), ("SGLang", sglang)]):
    col = COLORS[proj]
    dates = df_p["date"].values

    ax.plot(dates, df_p["additions_median"], color=col, lw=2.5, marker="o", ms=5,
            label="Median additions", zorder=5)
    ax.plot(dates, df_p["deletions_median"], color=col, lw=2.0, ls="--", marker="s", ms=4,
            label="Median deletions", zorder=4)

    ax.set_title(f"{proj} — Lines Changed per PR", fontsize=FS_TITLE-2, fontweight="bold", color=col)
    ax.set_xlabel("Month", fontsize=FS_LABEL)
    ax.set_ylabel("Lines", fontsize=FS_LABEL)
    ax.legend(fontsize=FS_LEGEND, loc="upper right", framealpha=0.9)
    fmt_xaxis(ax)
    x_min = df["date"].min() if proj == "SGLang" else df_p["date"].min()
    ax.set_xlim(x_min, df_p["date"].max())
    add_era_shading(ax, x_min, df_p["date"].max())

for ax, (proj, df_p) in zip(axes[1], [("vLLM", vllm), ("SGLang", sglang)]):
    col = COLORS[proj]
    dates = df_p["date"].values

    ax.plot(dates, df_p["files_median"], color=col, lw=2.5, marker="o", ms=5,
            label="Median files changed", zorder=5)

    x_num = df_p["month_num"].values
    y = df_p["files_median"].values
    valid = ~np.isnan(y)
    if valid.sum() > 3:
        slope, intercept, r, p_val, _ = stats.linregress(x_num[valid], y[valid])
        date_line = [df_p["date"].iloc[0], df_p["date"].iloc[-1]]
        y_line = [slope * x_num[0] + intercept, slope * x_num[-1] + intercept]
        ax.plot(date_line, y_line, color=col, lw=2.0, ls="-.", alpha=0.7,
                label=f"OLS: {slope:+.2f}/mo  r²={r**2:.2f}", zorder=6)

    ax.set_title(f"{proj} — Files Changed per PR", fontsize=FS_TITLE-2, fontweight="bold", color=col)
    ax.set_xlabel("Month", fontsize=FS_LABEL)
    ax.set_ylabel("Files", fontsize=FS_LABEL)
    ax.legend(fontsize=FS_LEGEND, loc="upper right", framealpha=0.9)
    fmt_xaxis(ax)
    x_min = df["date"].min() if proj == "SGLang" else df_p["date"].min()
    ax.set_xlim(x_min, df_p["date"].max())
    add_era_shading(ax, x_min, df_p["date"].max())

plt.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig("/mnt/results/fig7_pr_size_analysis_v6.png",
            dpi=500, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✓ Figure 7 saved")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 8 — Bot PR Prevalence Across Eras (NEW)
# ═══════════════════════════════════════════════════════════════════════════════
print("Generating Figure 8...")
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

for ax, (proj, df_d) in zip(axes, [("vLLM", vllm_dec), ("SGLang", sglang_dec)]):
    col = COLORS[proj]
    dates = df_d["date"].values
    human = df_d["prs_merged_human"].values
    bot = df_d["prs_merged_bot"].values
    bot_share = df_d["bot_share"].values * 100

    # Stacked area: human + bot
    ax.stackplot(dates, human, bot,
                 labels=["Human-authored PRs", "Bot-authored PRs"],
                 colors=[col, "#CC0000"],
                 alpha=0.75, zorder=2)

    # Bot share on twin axis
    ax2 = ax.twinx()
    ax2.plot(dates, bot_share, color="#CC0000", lw=2.2, ls="-",
             marker="s", ms=4, label="Bot PR share (%)", zorder=5)
    ax2.set_ylabel("Bot PR Share (%)", fontsize=FS_LABEL, color="#CC0000")
    ax2.tick_params(axis="y", labelcolor="#CC0000", labelsize=FS_TICK)
    ax2.set_ylim(0, max(bot_share) * 1.3 if max(bot_share) > 0 else 10)

    ax.set_title(proj, fontsize=FS_TITLE, fontweight="bold", color=col)
    ax.set_xlabel("Month", fontsize=FS_LABEL)
    ax.set_ylabel("PRs / Month", fontsize=FS_LABEL)
    ax.autoscale(axis="y")
    ylo, yhi = ax.get_ylim(); ax.set_ylim(max(ylo, 0), yhi * 1.25)
    x_min = df["date"].min() if proj == "SGLang" else df_d["date"].min()
    ax.set_xlim(x_min, df_d["date"].max())
    add_era_shading(ax, x_min, df_d["date"].max(), show_labels=True)

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2,
              fontsize=FS_LEGEND-1, loc="upper left", framealpha=0.9)
    fmt_xaxis(ax)

plt.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig("/mnt/results/fig8_bot_pr_prevalence_v1.png",
            dpi=500, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✓ Figure 8 saved")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 9 — Human vs. Bot Metric Comparison (NEW)
# ═══════════════════════════════════════════════════════════════════════════════
print("Generating Figure 9...")
fig, axes = plt.subplots(2, 3, figsize=(20, 12))

metrics_to_plot = [
    ("prs_merged", "PR Throughput", "PRs / Month", "prs_merged_human", "prs_merged_bot"),
    ("cycle_median", "Cycle Time (Median)", "Days", "cycle_median_human", "cycle_median_bot"),
    ("unique_authors", "Unique Authors", "Authors / Month", "unique_authors_human", "unique_authors_bot"),
    ("comment_mean", "Comment Density", "Comments / PR", "comment_mean_human", "comment_mean_bot"),
    ("prs_per_author", "PRs per Author", "PRs / Author / Month", "prs_per_author_human", None),
    ("bot_share", "Bot PR Share", "%", None, None),
]

for idx, (metric_key, title, ylabel, human_col, bot_col) in enumerate(metrics_to_plot):
    ax = axes[idx // 3, idx % 3]

    for proj, df_d in [("vLLM", vllm_dec), ("SGLang", sglang_dec)]:
        col = COLORS[proj]
        dates = df_d["date"].values

        if metric_key == "bot_share":
            # Special case: bot share percentage
            vals = df_d["bot_share"].values * 100
            ax.plot(dates, vals, color=col, lw=2.5, marker="o", ms=4,
                    label=proj, zorder=5)
        elif metric_key == "prs_per_author":
            # Special case: PRs per author (human only)
            vals = df_d["prs_per_author_human"].values
            ax.plot(dates, vals, color=col, lw=2.5, marker="o", ms=4,
                    label=f"{proj} (human)", zorder=5)
        else:
            # Human vs bot comparison
            if human_col and human_col in df_d.columns:
                human_vals = df_d[human_col].values
                ax.plot(dates, human_vals, color=col, lw=2.5, marker="o", ms=4,
                        label=f"{proj} (human)", zorder=5)

            if bot_col and bot_col in df_d.columns:
                bot_vals = df_d[bot_col].values
                valid = ~np.isnan(bot_vals)
                if valid.sum() > 0:
                    ax.plot(dates[valid], bot_vals[valid], color=col, lw=2.0, ls="--",
                            marker="s", ms=3, alpha=0.7, label=f"{proj} (bot)", zorder=4)

    ax.set_title(title, fontsize=FS_TITLE-2, fontweight="bold")
    ax.set_xlabel("Month", fontsize=FS_LABEL-2)
    ax.set_ylabel(ylabel, fontsize=FS_LABEL-2)
    ax.legend(fontsize=FS_LEGEND-2, loc="best", framealpha=0.9)
    fmt_xaxis(ax)
    ax.tick_params(labelsize=FS_TICK-2)

    # Add era shading
    x_min = df["date"].min()
    x_max = df_dec["date"].max()
    ax.set_xlim(x_min, x_max)
    add_era_shading(ax, x_min, x_max, show_labels=(idx < 3))

plt.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig("/mnt/results/fig9_human_vs_bot_metrics_v1.png",
            dpi=500, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("  ✓ Figure 9 saved")

print("\n✓ All 9 figures generated successfully.")
