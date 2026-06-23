#!/usr/bin/env python3
"""Plot Figure 5: Distribution of response length (words) across 8 models on FinIF-test.

Data source: /tmp/benchmark307_response_lengths.pkl
  (pickle dict keyed by model name, each value has "word_lengths" list)

Original output: lunwen/outputs/figures/fig_response_length_boxplot.png
"""

from __future__ import annotations

import pickle
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 13,
    "xtick.labelsize": 12,
    "ytick.labelsize": 11,
    "legend.fontsize": 11,
    "figure.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})

PKL_PATH = Path("/tmp/benchmark307_response_lengths.pkl")
OUTPUT_DIR = Path("/Users/minimax/Desktop/lunwen/outputs/figures")

MODEL_ORDER = [
    "GPT-5.5", "GPT-5", "GLM-5.1", "DS-V4-Pro", "DS-V4-Flash",
    "Qwen3.5-27B", "Qwen3.5-9B", "Qwen3.5-4B",
]
COLORS = [
    "#e74c3c", "#e67e22", "#27ae60", "#2980b9", "#3498db",
    "#8e44ad", "#9b59b6", "#7f8c8d",
]


def main() -> None:
    results = pickle.load(PKL_PATH.open("rb"))

    fig, ax = plt.subplots(figsize=(4.5, 3))

    data = [results[m]["word_lengths"] for m in MODEL_ORDER]
    bp = ax.boxplot(
        data,
        tick_labels=MODEL_ORDER,
        patch_artist=True,
        widths=0.55,
        showfliers=True,
        flierprops=dict(marker=".", markersize=2, alpha=0.4, linewidth=0),
        boxprops=dict(linewidth=0.6),
        whiskerprops=dict(linewidth=0.6),
        capprops=dict(linewidth=0.6),
        medianprops=dict(linewidth=0.8),
    )

    for patch, color in zip(bp["boxes"], COLORS):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    means = [np.mean(d) for d in data]
    ax.scatter(
        range(1, len(MODEL_ORDER) + 1),
        means,
        color="black",
        marker="D",
        s=12,
        zorder=5,
        label="Mean",
    )

    ax.set_ylabel("Response Length (words)")
    ax.tick_params(axis="x", rotation=35)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.2, axis="y")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_png = OUTPUT_DIR / "fig_response_length_boxplot.png"
    out_pdf = OUTPUT_DIR / "fig_response_length_boxplot.pdf"
    fig.savefig(out_png)
    fig.savefig(out_pdf)
    plt.close()
    print(f"Saved: {out_png}")
    print(f"Saved: {out_pdf}")

    # Summary stats
    print(f"\n{'Model':<16} {'Count':>7} {'Mean':>7} {'Median':>7} {'Min':>6} {'Max':>6} {'Std':>8}")
    for m in MODEL_ORDER:
        wl = results[m]["word_lengths"]
        print(f"{m:<16} {len(wl):>7} {np.mean(wl):>7.0f} {np.median(wl):>7.0f} "
              f"{min(wl):>6} {max(wl):>6} {np.std(wl):>8.0f}")


if __name__ == "__main__":
    main()
