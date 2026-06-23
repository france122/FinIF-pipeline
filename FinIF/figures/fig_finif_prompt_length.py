"""FinIF-test vs IFEval prompt length distribution (log-log histogram with mean lines)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUT = Path(__file__).resolve().parent.parent / "pdf" / "finif_prompt_length.pdf"

BENCHMARK307_PATH = ROOT / "outputs" / "benchmark" / "finif_v2_gpt55_targeted_benchmark307_20260616.jsonl"

WORD_RE = re.compile(r"\S+")


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def read_jsonl(path: Path) -> list:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# --- Load FinIF-test ---
finif_rows = read_jsonl(BENCHMARK307_PATH)
finif_words = [count_words(r.get("full_prompt", "")) for r in finif_rows]

# --- Load IFEval ---
try:
    from datasets import load_dataset
    ds = load_dataset("google/IFEval", split="train")
    ifeval_words = [count_words(r["prompt"]) for r in ds]
except Exception:
    ifeval_words = []

# --- Plot ---
fig, ax = plt.subplots(figsize=(7, 4.8))

min_word = min(min(finif_words), min(ifeval_words)) if ifeval_words else min(finif_words)
max_word = max(max(finif_words), max(ifeval_words)) if ifeval_words else max(finif_words)
bin_edges = np.logspace(math.log10(max(min_word, 5)), math.log10(max_word * 1.05), 26)

if ifeval_words:
    ax.hist(ifeval_words, bins=bin_edges, alpha=0.65, color='#F5BFA0', edgecolor='#E08050',
            linewidth=0.5, label='IFEval')
ax.hist(finif_words, bins=bin_edges, alpha=0.7, color='#4A90C4', edgecolor='#2E6FA0',
        linewidth=0.5, label='FinIF-test')

ax.set_xscale('log')
ax.set_yscale('log')
ax.set_xlabel('Prompt Length (words)', fontsize=20)
ax.set_ylabel('Count', fontsize=20)
ax.tick_params(axis='both', which='major', labelsize=18)
ax.tick_params(axis='both', which='minor', labelsize=16)

# Mean lines
if ifeval_words:
    mu_if = int(round(np.mean(ifeval_words)))
    ax.axvline(mu_if, color='#C0392B', linestyle='--', linewidth=2.2, zorder=5)
    ax.text(mu_if * 0.42, ax.get_ylim()[1] * 0.9, f'$\\mu$={mu_if}',
            fontsize=18, fontweight='bold', color='#C0392B')

mu_fin = int(round(np.mean(finif_words)))
ax.axvline(mu_fin, color='#1A5276', linestyle='--', linewidth=2.2, zorder=5)
ax.text(mu_fin * 1.08, ax.get_ylim()[1] * 0.9, f'$\\mu$={mu_fin}',
        fontsize=18, fontweight='bold', color='#1A5276')

ax.legend(fontsize=16, framealpha=0.9, loc='upper center', bbox_to_anchor=(0.5, 1.08))
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
fig.savefig(OUT, bbox_inches='tight', dpi=300)
print(f'Saved: {OUT}')
