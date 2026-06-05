"""FinIF 雷达图：按约束大类 & 子标签维度对比 10 模型通过率。"""

import json, glob, math
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).parent

# ── 1. 加载数据 ──────────────────────────────────────────────

with open(ROOT / "benchmark/eval_config_all.json") as f:
    constraints = json.load(f)["constraints"]

TAG_OF = {cid: c["tag"] for cid, c in constraints.items()}

CATEGORY_OF_TAG = {
    "F1": "Format", "F2": "Format", "F3": "Format", "F4": "Format",
    "F5": "Format", "F6": "Format", "F7": "Format",
    "N1": "Number", "N2": "Number", "N3": "Number",
    "L1": "Linguistic", "L2": "Linguistic", "L3": "Linguistic", "L4": "Linguistic",
    "S1": "Style", "S2": "Style", "S3": "Style", "S4": "Style",
    "C3": "Content", "C5": "Content",
}

TAG_LABELS = {
    "F1": "Section", "F2": "List", "F3": "Table", "F4": "JSON",
    "F5": "Quote", "F6": "Open/Close", "F7": "Special",
    "N1": "Word Cnt", "N2": "Elem Cnt", "N3": "Precision",
    "L1": "Keyword", "L2": "Forbidden", "L3": "Terminology", "L4": "Fin. Symbol",
    "S1": "Tone", "S2": "Role", "S3": "Coherence", "S4": "Rhetoric",
    "C3": "Perspective", "C5": "Conditional",
}

TAG_ORDER = ["F1","F2","F3","F4","F5","F6","F7",
             "N1","N2","N3",
             "L1","L2","L3","L4",
             "S1","S2","S3","S4",
             "C3","C5"]
CAT_ORDER = ["Format", "Number", "Linguistic", "Style", "Content"]

MODEL_DISPLAY = {
    "gpt5.4": "GPT-5.4", "gpt5.2": "GPT-5.2", "gpt5.1": "GPT-5.1", "gpt5": "GPT-5",
    "ds-v4-pro-thinking": "DS-V4-Pro-Think", "ds-v4-pro": "DS-V4-Pro",
    "ds-v4-flash": "DS-V4-Flash", "ds-v4-flash-thinking": "DS-V4-Flash-Think",
    "qwen3-8b": "Qwen3-8B", "qwen3-8b-sft": "Qwen3-8B-SFT",
}

PLOT_ORDER = [
    "gpt5.4", "gpt5.2", "gpt5", "gpt5.1",
    "ds-v4-pro-thinking", "ds-v4-pro", "ds-v4-flash", "ds-v4-flash-thinking",
    "qwen3-8b-sft", "qwen3-8b",
]

# ── 2. 计算各模型各 tag / category 通过率 ─────────────────────

def calc_pass_rates(results):
    tag_pass, tag_total = {}, {}
    for case_id, case_constraints in results.items():
        for cid, info in case_constraints.items():
            tag = TAG_OF.get(cid)
            if not tag:
                continue
            tag_total[tag] = tag_total.get(tag, 0) + 1
            if info.get("pass"):
                tag_pass[tag] = tag_pass.get(tag, 0) + 1
    tag_rates = {t: tag_pass.get(t, 0) / tag_total[t] for t in tag_total}
    cat_pass, cat_total = {}, {}
    for t in tag_total:
        cat = CATEGORY_OF_TAG.get(t, "?")
        cat_total[cat] = cat_total.get(cat, 0) + tag_total[t]
        cat_pass[cat] = cat_pass.get(cat, 0) + tag_pass.get(t, 0)
    cat_rates = {c: cat_pass.get(c, 0) / cat_total[c] for c in cat_total}
    return tag_rates, cat_rates

model_data = {}
for fpath in sorted(glob.glob(str(ROOT / "benchmark/scores/scores_*.json"))):
    with open(fpath) as f:
        data = json.load(f)
    key = data["model"]
    tag_rates, cat_rates = calc_pass_rates(data["results"])
    model_data[key] = {"tag": tag_rates, "cat": cat_rates}

# ── 3. 画雷达图 ──────────────────────────────────────────────

MODEL_STYLE = {
    "gpt5.4":              {"color": "#4472C4", "ls": "-", "lw": 1.8},  # blue
    "gpt5.2":              {"color": "#548235", "ls": "-", "lw": 1.8},  # dark green
    "gpt5":                {"color": "#C0392B", "ls": "-", "lw": 1.8},  # red
    "gpt5.1":              {"color": "#70AD47", "ls": "-", "lw": 1.8},  # lime green
    "ds-v4-pro-thinking":  {"color": "#ED7D31", "ls": "-", "lw": 1.8},  # orange
    "ds-v4-pro":           {"color": "#E377C2", "ls": "-", "lw": 1.8},  # pink
    "ds-v4-flash":         {"color": "#5B9BD5", "ls": "-", "lw": 1.8},  # light blue
    "ds-v4-flash-thinking":{"color": "#002060", "ls": "-", "lw": 1.8},  # dark navy
    "qwen3-8b-sft":        {"color": "#7030A0", "ls": "-", "lw": 1.8},  # purple
    "qwen3-8b":            {"color": "#00B0F0", "ls": "-", "lw": 1.8},  # cyan
}

def radar_chart(ax, labels, keys, model_values, title, rmin=0.4):
    n = len(labels)
    angles = np.linspace(0, 2 * math.pi, n, endpoint=False).tolist()
    angles += angles[:1]

    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=8)

    yticks = np.arange(rmin, 1.01, 0.1)
    ax.set_yticks(yticks)
    ax.set_yticklabels([f"{v:.1f}" for v in yticks], fontsize=6, color="grey")
    ax.set_ylim(rmin, 1.02)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=18)

    lines = []
    for key, vals in model_values:
        sty = MODEL_STYLE[key]
        data = [vals.get(k, 0) for k in keys] + [vals.get(keys[0], 0)]
        line, = ax.plot(angles, data, color=sty["color"], linewidth=sty["lw"],
                        linestyle=sty["ls"], label=MODEL_DISPLAY[key])
        ax.fill(angles, data, color=sty["color"], alpha=0.03)
        lines.append(line)
    return lines

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8),
                                subplot_kw=dict(projection="polar"))
fig.subplots_adjust(wspace=0.35, top=0.82, bottom=0.05)

ordered = [(k, model_data[k]) for k in PLOT_ORDER if k in model_data]

radar_chart(ax1, CAT_ORDER, CAT_ORDER,
            [(k, d["cat"]) for k, d in ordered],
            "(a) Primary Constraint Category", rmin=0.5)

lines = radar_chart(ax2, [TAG_LABELS[t] for t in TAG_ORDER], TAG_ORDER,
                    [(k, d["tag"]) for k, d in ordered],
                    "(b) Secondary Constraint Tag", rmin=0.1)

fig.legend(handles=lines, loc="upper center", ncol=5, fontsize=9,
           frameon=True, fancybox=True, shadow=False,
           bbox_to_anchor=(0.5, 0.97))

fig.suptitle("FinIF Benchmark: Model Performance by Constraint Category",
             fontsize=14, fontweight="bold", y=1.0)

out = ROOT / "docs/radar_by_constraint.png"
fig.savefig(out, dpi=200, bbox_inches="tight")
print(f"Saved → {out}")
plt.close()
