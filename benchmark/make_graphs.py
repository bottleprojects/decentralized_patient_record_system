#!/usr/bin/env python3
"""
Generate publication-quality graphs and summary statistics for DPRMS Real-World Benchmark.
Exports 200 DPI PNG charts to benchmark/report_output/ and summary_table.csv.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent
RESULTS_CSV = BENCHMARK_DIR / "results.csv"
OUTPUT_DIR = BENCHMARK_DIR / "report_output"
SUMMARY_CSV = BENCHMARK_DIR / "summary_table.csv"

# Styling constants
COLOR_SUPABASE = "#10b981"  # Emerald Green
COLOR_IPFS = "#3b82f6"      # Tech Blue
COLOR_SUPABASE_DARK = "#059669"
COLOR_IPFS_DARK = "#2563eb"
COLOR_ACCENT = "#8b5cf6"    # Purple
DPI = 200


def setup_plot_style():
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.labelweight": "semibold",
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.autolayout": True,
        "figure.titlesize": 14,
    })


def generate_summary_table(df):
    """Generates summary_table.csv with runs, median, mean, p95, std dev, failure rate."""
    records = []
    
    # Group by site, file_size_kb, operation, network_profile
    grouped = df.groupby(["site", "file_size_kb", "operation", "network_profile"])
    
    for (site, size_kb, op, profile), group in grouped:
        total_runs = len(group)
        successful = group[group["success"] == True]
        success_count = len(successful)
        failure_rate = round((total_runs - success_count) / total_runs * 100.0, 2)
        
        if success_count > 0:
            times = successful["time_ms"]
            median_val = round(times.median(), 2)
            mean_val = round(times.mean(), 2)
            p95_val = round(np.percentile(times, 95), 2)
            std_val = round(times.std(), 2) if len(times) > 1 else 0.0
        else:
            median_val = mean_val = p95_val = std_val = 0.0

        records.append({
            "site": site,
            "file_size_kb": size_kb,
            "operation": op,
            "network_profile": profile,
            "runs": total_runs,
            "successful_runs": success_count,
            "median_ms": median_val,
            "mean_ms": mean_val,
            "p95_ms": p95_val,
            "std_dev_ms": std_val,
            "failure_rate_pct": failure_rate
        })
    
    summary_df = pd.DataFrame(records)
    summary_df.sort_values(by=["network_profile", "operation", "file_size_kb", "site"], inplace=True)
    summary_df.to_csv(SUMMARY_CSV, index=False)
    print(f"[SUMMARY] Exported {len(summary_df)} aggregated metric rows to {SUMMARY_CSV}")
    return summary_df


def plot_grouped_upload_bars(df):
    """1. Grouped bar charts of median upload time per file size, Supabase vs IPFS, one chart per network profile."""
    upload_df = df[(df["operation"] == "upload_ui") & (df["success"] == True) & (df["file_size_kb"] > 0)]
    if upload_df.empty:
        return

    profiles = upload_df["network_profile"].unique()
    for profile in profiles:
        prof_data = upload_df[upload_df["network_profile"] == profile]
        sizes = sorted(prof_data["file_size_kb"].unique())
        
        supabase_medians = []
        supabase_errs = []
        ipfs_medians = []
        ipfs_errs = []
        
        for s in sizes:
            sub_s = prof_data[(prof_data["file_size_kb"] == s) & (prof_data["site"] == "supabase")]["time_ms"]
            ip_s = prof_data[(prof_data["file_size_kb"] == s) & (prof_data["site"] == "ipfs")]["time_ms"]
            
            supabase_medians.append(sub_s.median() if not sub_s.empty else 0)
            supabase_errs.append(sub_s.std() if len(sub_s) > 1 else 0)
            ipfs_medians.append(ip_s.median() if not ip_s.empty else 0)
            ipfs_errs.append(ip_s.std() if len(ip_s) > 1 else 0)
            
        x = np.arange(len(sizes))
        width = 0.35

        fig, ax = plt.subplots(figsize=(8, 5))
        rects1 = ax.bar(x - width/2, supabase_medians, width, yerr=supabase_errs, capsize=4,
                        label="Supabase Storage (Site A)", color=COLOR_SUPABASE, edgecolor="#065f46", alpha=0.9)
        rects2 = ax.bar(x + width/2, ipfs_medians, width, yerr=ipfs_errs, capsize=4,
                        label="IPFS / Pinata (Site B)", color=COLOR_IPFS, edgecolor="#1e40af", alpha=0.9)

        ax.set_ylabel("Median Upload Duration (ms)")
        ax.set_xlabel("Payload Size")
        ax.set_title(f"Median Upload Duration by Payload Size ({profile})\n[UI Trigger to Confirmation]")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{s} KB" if s < 1024 else f"{s//1024} MB" for s in sizes])
        ax.legend(frameon=True)
        ax.grid(True, linestyle="--", alpha=0.4, axis="y")

        # Value labels
        def autolabel(rects):
            for rect in rects:
                height = rect.get_height()
                if height > 0:
                    ax.annotate(f"{height:.0f} ms",
                                xy=(rect.get_x() + rect.get_width() / 2, height),
                                xytext=(0, 3), textcoords="offset points",
                                ha="center", va="bottom", fontsize=8, fontweight="bold")

        autolabel(rects1)
        autolabel(rects2)

        safe_name = profile.lower().replace(" ", "_")
        fig.savefig(OUTPUT_DIR / f"upload_time_{safe_name}.png", dpi=DPI)
        plt.close(fig)
        print(f"[GRAPH 1] Generated upload_time_{safe_name}.png")


def plot_retrieval_cold_vs_warm(df):
    """2. Retrieval cold vs warm, grouped layout."""
    ret_df = df[df["operation"].isin(["retrieval_cold", "retrieval_warm"]) & (df["success"] == True) & (df["file_size_kb"] > 0)]
    if ret_df.empty:
        return

    profiles = ret_df["network_profile"].unique()
    for profile in profiles:
        prof_data = ret_df[ret_df["network_profile"] == profile]
        sizes = sorted(prof_data["file_size_kb"].unique())
        
        # 4 bars per size: Supabase Cold, Supabase Warm, IPFS Cold, IPFS Warm
        x = np.arange(len(sizes))
        width = 0.2

        fig, ax = plt.subplots(figsize=(10, 5))
        
        sub_cold = [prof_data[(prof_data["file_size_kb"] == s) & (prof_data["site"] == "supabase") & (prof_data["operation"] == "retrieval_cold")]["time_ms"].median() for s in sizes]
        sub_warm = [prof_data[(prof_data["file_size_kb"] == s) & (prof_data["site"] == "supabase") & (prof_data["operation"] == "retrieval_warm")]["time_ms"].median() for s in sizes]
        ip_cold = [prof_data[(prof_data["file_size_kb"] == s) & (prof_data["site"] == "ipfs") & (prof_data["operation"] == "retrieval_cold")]["time_ms"].median() for s in sizes]
        ip_warm = [prof_data[(prof_data["file_size_kb"] == s) & (prof_data["site"] == "ipfs") & (prof_data["operation"] == "retrieval_warm")]["time_ms"].median() for s in sizes]

        ax.bar(x - 1.5*width, sub_cold, width, label="Supabase (Cold Fetch)", color=COLOR_SUPABASE, alpha=0.9)
        ax.bar(x - 0.5*width, sub_warm, width, label="Supabase (Warm Cache)", color=COLOR_SUPABASE, hatch="//", alpha=0.6)
        ax.bar(x + 0.5*width, ip_cold, width, label="IPFS (Cold Gateway)", color=COLOR_IPFS, alpha=0.9)
        ax.bar(x + 1.5*width, ip_warm, width, label="IPFS (Warm Cache)", color=COLOR_IPFS, hatch="//", alpha=0.6)

        ax.set_ylabel("Median Retrieval Time (ms)")
        ax.set_xlabel("Payload Size")
        ax.set_title(f"Record Retrieval: Cold vs Warm Cache ({profile})")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{s} KB" if s < 1024 else f"{s//1024} MB" for s in sizes])
        ax.legend(frameon=True)
        ax.grid(True, linestyle="--", alpha=0.4, axis="y")

        safe_name = profile.lower().replace(" ", "_")
        fig.savefig(OUTPUT_DIR / f"retrieval_cold_warm_{safe_name}.png", dpi=DPI)
        plt.close(fig)
        print(f"[GRAPH 2] Generated retrieval_cold_warm_{safe_name}.png")


def plot_page_load_comparison(df):
    """3. Page load (FCP, LCP, Total) comparison for Login & Dashboard."""
    page_ops = ["page_load_login_fcp", "page_load_login_lcp", "page_load_login_total",
                "page_load_dashboard_fcp", "page_load_dashboard_lcp", "page_load_dashboard_total"]
    page_df = df[df["operation"].isin(page_ops) & (df["success"] == True)]
    if page_df.empty:
        return

    grouped = page_df.groupby(["site", "operation"])["time_ms"].median().unstack(level=0)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(grouped))
    width = 0.35

    sub_vals = grouped["supabase"] if "supabase" in grouped else [0]*len(grouped)
    ip_vals = grouped["ipfs"] if "ipfs" in grouped else [0]*len(grouped)

    ax.bar(x - width/2, sub_vals, width, label="Site A (Supabase/Railway)", color=COLOR_SUPABASE)
    ax.bar(x + width/2, ip_vals, width, label="Site B (IPFS/Vercel+Render)", color=COLOR_IPFS)

    labels = [op.replace("page_load_", "").replace("_", " ").upper() for op in grouped.index]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Median Latency (ms)")
    ax.set_title("Frontend Core Web Vitals & Page Load Navigation Timing (FCP, LCP, Total)")
    ax.legend(frameon=True)
    ax.grid(True, linestyle="--", alpha=0.4, axis="y")

    fig.savefig(OUTPUT_DIR / "page_load_comparison.png", dpi=DPI)
    plt.close(fig)
    print("[GRAPH 3] Generated page_load_comparison.png")


def plot_time_vs_size_lines(df):
    """4. Line chart of time vs file size under each network profile."""
    ops = ["upload_ui", "retrieval_cold"]
    data = df[df["operation"].isin(ops) & (df["success"] == True) & (df["file_size_kb"] > 0)]
    if data.empty:
        return

    profiles = data["network_profile"].unique()
    for profile in profiles:
        prof_data = data[data["network_profile"] == profile]
        fig, ax = plt.subplots(figsize=(8, 5))
        
        sizes = sorted(prof_data["file_size_kb"].unique())
        sizes_mb = [s / 1024 for s in sizes]

        for site, color, label_prefix in [("supabase", COLOR_SUPABASE, "Supabase"), ("ipfs", COLOR_IPFS, "IPFS")]:
            sub_up = [prof_data[(prof_data["site"] == site) & (prof_data["operation"] == "upload_ui") & (prof_data["file_size_kb"] == s)]["time_ms"].median() for s in sizes]
            sub_ret = [prof_data[(prof_data["site"] == site) & (prof_data["operation"] == "retrieval_cold") & (prof_data["file_size_kb"] == s)]["time_ms"].median() for s in sizes]
            
            ax.plot(sizes_mb, sub_up, marker="o", linewidth=2.5, color=color, label=f"{label_prefix} Upload")
            ax.plot(sizes_mb, sub_ret, marker="s", linestyle="--", linewidth=2, color=color, alpha=0.75, label=f"{label_prefix} Retrieval (Cold)")

        ax.set_xlabel("Payload Size (MB)")
        ax.set_ylabel("Median Time (ms)")
        ax.set_title(f"Scaling Characteristics: Latency vs Payload Size ({profile})")
        ax.legend(frameon=True)
        ax.grid(True, linestyle="--", alpha=0.4)

        safe_name = profile.lower().replace(" ", "_")
        fig.savefig(OUTPUT_DIR / f"time_vs_size_lines_{safe_name}.png", dpi=DPI)
        plt.close(fig)
        print(f"[GRAPH 4] Generated time_vs_size_lines_{safe_name}.png")


def plot_consistency_boxplots_and_failures(df):
    """5. Box plots showing consistency, plus failure rate chart."""
    upload_df = df[(df["operation"] == "upload_ui") & (df["file_size_kb"] > 0)]
    if upload_df.empty:
        return

    # Boxplot of 1MB upload consistency
    one_mb = upload_df[(upload_df["file_size_kb"] == 1024) & (upload_df["success"] == True)]
    if not one_mb.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        
        groups = []
        labels = []
        colors = []
        for profile in sorted(one_mb["network_profile"].unique()):
            for site in ["supabase", "ipfs"]:
                subset = one_mb[(one_mb["network_profile"] == profile) & (one_mb["site"] == site)]["time_ms"]
                if not subset.empty:
                    groups.append(subset.values)
                    labels.append(f"{'Supabase' if site == 'supabase' else 'IPFS'}\n({profile})")
                    colors.append(COLOR_SUPABASE if site == "supabase" else COLOR_IPFS)

        bp = ax.boxplot(groups, tick_labels=labels, patch_artist=True, medianprops=dict(color="black", linewidth=1.5))
        for patch, c in zip(bp['boxes'], colors):
            patch.set_facecolor(c)
            patch.set_alpha(0.7)

        ax.set_ylabel("Upload Time (ms)")
        ax.set_title("Upload Latency Distribution & Variance (1 MB Payload)")
        ax.grid(True, linestyle="--", alpha=0.4, axis="y")
        fig.savefig(OUTPUT_DIR / "upload_consistency_boxplot.png", dpi=DPI)
        plt.close(fig)
        print("[GRAPH 5A] Generated upload_consistency_boxplot.png")

    # Failure rate chart
    fig, ax = plt.subplots(figsize=(8, 4))
    sites = ["supabase", "ipfs"]
    fail_rates = []
    for site in sites:
        site_runs = df[df["site"] == site]
        total = len(site_runs)
        fails = len(site_runs[site_runs["success"] == False])
        rate = (fails / total * 100.0) if total > 0 else 0
        fail_rates.append(rate)

    bars = ax.bar(["Supabase Storage (Site A)", "IPFS / Pinata (Site B)"], fail_rates, color=[COLOR_SUPABASE, COLOR_IPFS], width=0.4)
    ax.set_ylabel("Failure Rate (%)")
    ax.set_title("Reliability Comparison: Request Failure Rate Across All Runs")
    ax.set_ylim(0, max(10, max(fail_rates) * 1.5 if fail_rates else 10))
    ax.grid(True, linestyle="--", alpha=0.4, axis="y")
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")

    fig.savefig(OUTPUT_DIR / "failure_rate_comparison.png", dpi=DPI)
    plt.close(fig)
    print("[GRAPH 5B] Generated failure_rate_comparison.png")


def plot_cold_start_comparison(df):
    """6. Host initial response latency / cold start comparison."""
    cold_df = df[df["operation"] == "backend_cold_start"]
    if cold_df.empty:
        return

    fig, ax = plt.subplots(figsize=(7, 4.5))
    sites = ["supabase", "ipfs"]
    medians = []
    labels = ["Railway (Site A Backend)", "Render (Site B Backend)"]
    colors = [COLOR_SUPABASE, COLOR_IPFS]

    for site in sites:
        vals = cold_df[cold_df["site"] == site]["time_ms"]
        medians.append(vals.median() if not vals.empty else 0)

    bars = ax.bar(labels, medians, color=colors, width=0.4)
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Backend Initial Health Probe & Cold Start Response Latency")
    ax.grid(True, linestyle="--", alpha=0.4, axis="y")
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f"{h:.1f} ms", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")

    fig.savefig(OUTPUT_DIR / "backend_cold_start.png", dpi=DPI)
    plt.close(fig)
    print("[GRAPH 6] Generated backend_cold_start.png")


def main():
    if not RESULTS_CSV.exists():
        print(f"Error: {RESULTS_CSV} not found! Run run_browser_benchmark.py first.")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    setup_plot_style()

    df = pd.read_csv(RESULTS_CSV)
    print(f"Loaded {len(df)} rows from {RESULTS_CSV}")

    generate_summary_table(df)
    plot_grouped_upload_bars(df)
    plot_retrieval_cold_vs_warm(df)
    plot_page_load_comparison(df)
    plot_time_vs_size_lines(df)
    plot_consistency_boxplots_and_failures(df)
    plot_cold_start_comparison(df)

    print("\nAll graphs and summary statistics generated successfully in benchmark/report_output/!")


if __name__ == "__main__":
    main()
