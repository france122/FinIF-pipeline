#!/usr/bin/env python3
"""FinIF 任务分类体系 — 旭日图（sunburst chart）"""
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from pathlib import Path

OUT_PATH = Path(__file__).resolve().with_name('task_taxonomy_chart.png')

matplotlib.rcParams['font.family'] = ['STHeiti', 'Heiti TC', 'Songti SC', 'PingFang HK', 'Arial']
matplotlib.rcParams['axes.unicode_minus'] = False

# ─── L1 (inner ring): 3 major categories ─────────────────
l1_labels = ['数据提取\n与计算', '分析与\n评估', '推理与\n合规']
l1_sizes  = [45, 33, 22]
l1_colors = ['#CFA435', '#5DA54C', '#4585BD']

# ─── L2 (outer ring): 11 subcategories ───────────────────
l2_info = [
    # (label,        cases, parent_l1_idx)
    ('基础计算',       19,   0),
    ('指标分析',       12,   0),
    ('结构化展示',     14,   0),
    ('综合分析',        8,   1),
    ('多维评估',        6,   1),
    ('趋势对比',        6,   1),
    ('风险评估',        7,   1),
    ('格式密集',        6,   1),
    ('复杂推理',        7,   2),
    ('综合报告',        8,   2),
    ('高阶推导',        7,   2),
]

l2_names  = [d[0] for d in l2_info]
l2_sizes  = [d[1] for d in l2_info]
l2_parent = [d[2] for d in l2_info]

# ─── Subtypes (outermost ring): 31 items ─────────────────
sub_info = [
    # T1.1 (19)
    ('涨跌幅计算',   3.8, 0), ('收益率计算', 3.8, 0), ('宏观统计', 3.8, 0),
    ('资金流向',     3.8, 0), ('同比计算',   3.8, 0),
    # T1.2 (12)
    ('减持增持',     3.0, 0), ('盈利能力',   3.0, 0),
    ('估值指标',     3.0, 0), ('经营效率',   3.0, 0),
    # T1.3 (14)
    ('处罚摘要',     3.5, 0), ('数据结构化', 3.5, 0),
    ('条款提取',     3.5, 0), ('问答整理',   3.5, 0),
    # T2.1 (8)
    ('业绩分析',     4.0, 1), ('财务评估',   4.0, 1),
    # T2.2 (6)
    ('板块对比',     3.0, 1), ('结构分析',   3.0, 1),
    # T2.3 (6)
    ('趋势分析',     3.0, 1), ('竞争对比',   3.0, 1),
    # T2.4 (7)
    ('信用风险',     3.5, 1), ('市场风险',   3.5, 1),
    # T2.5 (6)
    ('摘要分析',     3.0, 1), ('结构化报告', 3.0, 1),
    # T3.1 (7)
    ('异常审查',     2.33, 2), ('持股推理', 2.33, 2), ('成本逆推', 2.34, 2),
    # T3.2 (8)
    ('审计报告',     4.0, 2), ('合规报告',   4.0, 2),
    # T3.3 (7)
    ('数据核验',     2.33, 2), ('逻辑一致', 2.33, 2), ('交叉推导', 2.34, 2),
]
sub_names  = [d[0] for d in sub_info]
sub_sizes  = [d[1] for d in sub_info]
sub_parent = [d[2] for d in sub_info]

# ─── Color generation ────────────────────────────────────
def make_shades(base_hex, parent_indices, darken_range=(0.70, 1.0), lighten=0.25):
    """Generate gradient shades within each parent group."""
    colors = []
    for pi in sorted(set(parent_indices)):
        indices = [i for i, p in enumerate(parent_indices) if p == pi]
        n = len(indices)
        for j, idx in enumerate(indices):
            t = j / max(n - 1, 1)
            factor = darken_range[0] + (darken_range[1] - darken_range[0]) * t
            parent_rgb = matplotlib.colors.to_rgb(l1_colors[pi])
            c = tuple(min(1.0, ch * factor + (1 - factor) * lighten) for ch in parent_rgb)
            colors.append((idx, c))
    colors.sort(key=lambda x: x[0])
    return [c for _, c in colors]

l2_colors = make_shades(None, l2_parent, darken_range=(0.72, 0.98), lighten=0.30)
sub_colors = make_shades(None, sub_parent, darken_range=(0.55, 0.92), lighten=0.40)

# ─── Plot ─────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 10), dpi=150)
ax.set_aspect('equal')

# Ring 1: L1 (inner)
w1, _ = ax.pie(l1_sizes, radius=0.42, colors=l1_colors,
    wedgeprops=dict(width=0.18, edgecolor='white', linewidth=2.5),
    startangle=90, counterclock=False)

# Ring 2: L2 (middle)
w2, _ = ax.pie(l2_sizes, radius=0.68, colors=l2_colors,
    wedgeprops=dict(width=0.26, edgecolor='white', linewidth=1.8),
    startangle=90, counterclock=False)

# Ring 3: Subtypes (outer)
w3, _ = ax.pie(sub_sizes, radius=1.0, colors=sub_colors,
    wedgeprops=dict(width=0.32, edgecolor='white', linewidth=1.2),
    startangle=90, counterclock=False)

# Center circle
ax.add_patch(plt.Circle((0, 0), 0.24, fc='white', ec='#999', lw=1.5, zorder=10))
ax.text(0, 0.03, 'FinIF', ha='center', va='center',
        fontsize=20, fontweight='bold', zorder=11)
ax.text(0, -0.06, '任务体系', ha='center', va='center',
        fontsize=11, color='#555', zorder=11)

# ─── Label helpers ────────────────────────────────────────
def tangential_rot(ang_deg):
    """Rotation for text tangent to the circle, always readable."""
    rot = ang_deg - 90
    while rot > 90:  rot -= 180
    while rot < -90: rot += 180
    return rot

def radial_rot_ha(ang_deg):
    """Rotation + ha for text pointing radially outward, always readable."""
    ang = ang_deg % 360
    if 90 < ang < 270:
        return ang + 180, 'right'
    return ang, 'left'

# Inner ring labels (tangential, inside the ring)
for wedge, label in zip(w1, l1_labels):
    ang = (wedge.theta1 + wedge.theta2) / 2.0
    r = 0.33
    x = r * np.cos(np.deg2rad(ang))
    y = r * np.sin(np.deg2rad(ang))
    rot = tangential_rot(ang)
    ax.text(x, y, label, ha='center', va='center',
            fontsize=13, fontweight='bold', color='#222',
            rotation=rot, rotation_mode='anchor', zorder=12,
            linespacing=1.1)

# Middle ring labels (tangential, inside the ring)
for wedge, label in zip(w2, l2_names):
    ang = (wedge.theta1 + wedge.theta2) / 2.0
    span = abs(wedge.theta2 - wedge.theta1)
    r = 0.55
    x = r * np.cos(np.deg2rad(ang))
    y = r * np.sin(np.deg2rad(ang))
    rot = tangential_rot(ang)
    fs = 10 if span > 18 else 9
    ax.text(x, y, label, ha='center', va='center',
            fontsize=fs, fontweight='bold', color='#222',
            rotation=rot, rotation_mode='anchor', zorder=12)

# Outer ring labels (radial, outside the ring)
for wedge, label in zip(w3, sub_names):
    ang = (wedge.theta1 + wedge.theta2) / 2.0
    span = abs(wedge.theta2 - wedge.theta1)
    r = 1.04
    x = r * np.cos(np.deg2rad(ang))
    y = r * np.sin(np.deg2rad(ang))
    rot, ha = radial_rot_ha(ang)
    fs = 9 if span > 12 else 8
    ax.text(x, y, label, ha=ha, va='center',
            fontsize=fs, color='#333',
            rotation=rot, rotation_mode='anchor')

# Subtitle
ax.text(0, -1.35, '(a) FinIF 任务分类体系', ha='center', va='center',
        fontsize=18, fontweight='bold')

ax.set_xlim(-1.45, 1.45)
ax.set_ylim(-1.50, 1.20)

plt.savefig(OUT_PATH, dpi=200, bbox_inches='tight', facecolor='white')
print(f'Saved to {OUT_PATH}')
plt.close()
