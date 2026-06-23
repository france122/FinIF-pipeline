#!/usr/bin/env python3
"""Build a clean Figure 1 case study for the FinIF paper."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle


OUTPUT_DIR = Path("paper/figures")
OUTPUT_PNG = OUTPUT_DIR / "figure1_finif_failures.png"
OUTPUT_PDF = OUTPUT_DIR / "figure1_finif_failures.pdf"


BLUE = "#6d9fe0"
BLUE_DARK = "#2f5e9c"
BLUE_LINE = "#b8cbe6"
GREEN = "#d8f0a7"
YELLOW = "#f8e29c"
GRAY = "#dfe3eb"
RED_BG = "#f5d6d6"
TEXT = "#1f2937"
MUTED = "#667085"
RED = "#db3a34"
GREEN_OK = "#1f9d55"


def rounded_box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    face: str,
    edge: str,
    radius: float = 0.02,
    lw: float = 1.6,
) -> None:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.01,rounding_size={radius}",
        linewidth=lw,
        edgecolor=edge,
        facecolor=face,
        transform=ax.transAxes,
    )
    ax.add_patch(patch)


def dashed_panel(ax: plt.Axes, x: float, y: float, w: float, h: float) -> None:
    panel = Rectangle(
        (x, y),
        w,
        h,
        linewidth=1.3,
        edgecolor=BLUE_LINE,
        facecolor="white",
        linestyle=(0, (2, 2)),
        transform=ax.transAxes,
    )
    ax.add_patch(panel)


def badge(ax: plt.Axes, x: float, y: float, n: int) -> None:
    circ = Circle((x, y), 0.015, transform=ax.transAxes, facecolor="#4f87d5", edgecolor="white", linewidth=1.2)
    ax.add_patch(circ)
    ax.text(
        x,
        y,
        str(n),
        ha="center",
        va="center",
        fontsize=9.5,
        fontweight="bold",
        color="white",
        transform=ax.transAxes,
    )


def mark(ax: plt.Axes, x: float, y: float, ok: bool) -> None:
    ax.text(
        x,
        y,
        "✓" if ok else "✗",
        ha="center",
        va="center",
        fontsize=24,
        fontweight="bold",
        color=GREEN_OK if ok else RED,
        transform=ax.transAxes,
    )


def draw() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(14.5, 7.9))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    fig.patch.set_facecolor("white")

    rounded_box(ax, 0.18, 0.90, 0.64, 0.07, BLUE, BLUE, radius=0.012)
    ax.text(
        0.50,
        0.935,
        "A Severe GPT-5.5 Failure on a Financial IF Task",
        ha="center",
        va="center",
        fontsize=20,
        fontweight="bold",
        fontstyle="italic",
        color="white",
        transform=ax.transAxes,
    )
    ax.text(
        0.50,
        0.875,
        "FinIF hard300 example item: client review report / credit-quality migration monitor",
        ha="center",
        va="center",
        fontsize=12.5,
        color=MUTED,
        transform=ax.transAxes,
    )

    rounded_box(ax, 0.19, 0.79, 0.62, 0.055, BLUE, BLUE, radius=0.012)
    ax.text(
        0.50,
        0.817,
        "Financial Prompt with Multiple Delivery Constraints",
        ha="center",
        va="center",
        fontsize=17,
        fontweight="bold",
        fontstyle="italic",
        color="white",
        transform=ax.transAxes,
    )
    dashed_panel(ax, 0.06, 0.57, 0.88, 0.20)

    ax.text(
        0.075,
        0.727,
        "Complete a credit-quality migration monitor for Elm Corporate Bond Ladder.",
        fontsize=16,
        fontstyle="italic",
        color=TEXT,
        transform=ax.transAxes,
    )

    ax.add_patch(Rectangle((0.54, 0.695), 0.27, 0.038, transform=ax.transAxes, facecolor=GREEN, edgecolor="none"))
    ax.text(0.545, 0.714, "Identify downgraded holdings.", fontsize=16, fontweight="bold", color=TEXT, transform=ax.transAxes)

    ax.text(0.075, 0.670, "Connect each final action to the active evidence and governing rule.", fontsize=16, color=TEXT, transform=ax.transAxes)
    ax.add_patch(Rectangle((0.56, 0.636), 0.26, 0.038, transform=ax.transAxes, facecolor=GREEN, edgecolor="none"))
    ax.text(0.565, 0.655, "single evidence-rule-action chain.", fontsize=16, fontweight="bold", color=TEXT, transform=ax.transAxes)

    ax.add_patch(Rectangle((0.075, 0.606), 0.46, 0.038, transform=ax.transAxes, facecolor=GRAY, edgecolor="none"))
    ax.text(0.081, 0.625, "Keep active source labels beside facts, figures, and decisions.", fontsize=16, fontweight="bold", color="#374151", transform=ax.transAxes)

    ax.add_patch(Rectangle((0.075, 0.580), 0.48, 0.038, transform=ax.transAxes, facecolor=GRAY, edgecolor="none"))
    ax.text(0.081, 0.599, "For as-of-date tests, show timing status and business implication.", fontsize=15.4, color="#4b5563", transform=ax.transAxes)

    ax.add_patch(Rectangle((0.61, 0.580), 0.22, 0.038, transform=ax.transAxes, facecolor=YELLOW, edgecolor="none"))
    ax.text(0.615, 0.599, "Name any required approver.", fontsize=15.6, color="#6b7280", transform=ax.transAxes)

    badge(ax, 0.88, 0.728, 1)
    badge(ax, 0.04, 0.672, 2)
    badge(ax, 0.89, 0.643, 3)
    badge(ax, 0.04, 0.597, 4)
    badge(ax, 0.73, 0.594, 5)

    rounded_box(ax, 0.32, 0.49, 0.36, 0.055, BLUE, BLUE, radius=0.012)
    ax.text(
        0.50,
        0.517,
        "Model Response",
        ha="center",
        va="center",
        fontsize=17,
        fontweight="bold",
        fontstyle="italic",
        color="white",
        transform=ax.transAxes,
    )
    dashed_panel(ax, 0.06, 0.14, 0.88, 0.31)

    ax.text(
        0.11,
        0.392,
        "**Credit-Quality Migration Monitor — Elm Corporate Bond Ladder**",
        fontsize=16,
        fontweight="bold",
        color=TEXT,
        transform=ax.transAxes,
    )

    ax.text(0.11, 0.343, "1. Downgraded holdings identified:", fontsize=16, color=TEXT, transform=ax.transAxes)
    ax.add_patch(Rectangle((0.39, 0.321), 0.43, 0.042, transform=ax.transAxes, facecolor="#d9f0dd", edgecolor="none"))
    ax.text(0.395, 0.343, "North Harbor Telecom -> BB+; Western Medical REIT -> BBB-.", fontsize=16, color=TEXT, transform=ax.transAxes)

    ax.text(0.11, 0.294, "2. Average portfolio quality test: BBB+ is below A-; should be flagged for review.", fontsize=16, color=TEXT, transform=ax.transAxes)
    ax.text(0.11, 0.245, "5. Required approver: not named in the packet.", fontsize=16, color=TEXT, transform=ax.transAxes)
    ax.text(0.59, 0.245, "As-of date tested: February 28, 2026.", fontsize=16, color=TEXT, transform=ax.transAxes)
    ax.text(0.11, 0.196, "Next action: escalate North Harbor Telecom for BB+ review ...", fontsize=16, color=TEXT, transform=ax.transAxes)

    ax.add_patch(Rectangle((0.11, 0.223), 0.31, 0.042, transform=ax.transAxes, facecolor=RED_BG, edgecolor="none"))
    ax.add_patch(Rectangle((0.59, 0.223), 0.23, 0.042, transform=ax.transAxes, facecolor=RED_BG, edgecolor="none"))
    ax.add_patch(Rectangle((0.11, 0.174), 0.35, 0.042, transform=ax.transAxes, facecolor=RED_BG, edgecolor="none"))

    mark(ax, 0.84, 0.353, True)
    badge(ax, 0.83, 0.353, 1)

    mark(ax, 0.42, 0.185, False)
    badge(ax, 0.41, 0.185, 2)

    mark(ax, 0.21, 0.295, False)
    badge(ax, 0.20, 0.295, 3)

    mark(ax, 0.84, 0.245, False)
    badge(ax, 0.83, 0.245, 4)

    mark(ax, 0.43, 0.245, False)
    badge(ax, 0.42, 0.245, 5)

    ax.text(
        0.12,
        0.104,
        "2 no evidence-rule-action chain   3 no active source labels beside facts",
        fontsize=12.8,
        color="#8b1e1e",
        transform=ax.transAxes,
    )
    ax.text(
        0.12,
        0.078,
        "4 as-of-date test lacks timing status   5 required approver is missing",
        fontsize=12.8,
        color="#8b1e1e",
        transform=ax.transAxes,
    )

    fig.savefig(OUTPUT_PNG, dpi=220, bbox_inches="tight")
    fig.savefig(OUTPUT_PDF, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    draw()
