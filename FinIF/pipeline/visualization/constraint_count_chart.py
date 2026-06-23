#!/usr/bin/env python3
"""约束数量对提示级准确率的影响 — matplotlib 默认色环风格"""
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from pathlib import Path

OUT_PATH = Path(__file__).resolve().with_name('constraint_count_chart.png')

matplotlib.rcParams['font.family'] = ['STHeiti', 'Heiti TC', 'Songti SC', 'PingFang HK', 'Arial']
matplotlib.rcParams['axes.unicode_minus'] = False

x = [1, 2, 3, 4, 5]

data = [
    ('GPT-5.4',           [100.0, 90.0, 86.7, 85.0, 80.0], '-',  'o'),
    ('GPT-5.2',           [100.0, 90.0, 86.7, 80.0, 80.0], '-',  's'),
    ('GPT-5',             [86.7, 80.0, 76.7, 85.0, 53.3],  '-',  '^'),
    ('GPT-5.1',           [100.0, 85.0, 70.0, 35.0, 60.0], '--', '*'),
    ('DS-V4-Pro-Think',   [93.3, 80.0, 83.3, 75.0, 46.7],  '-',  'D'),
    ('DS-V4-Pro',         [86.7, 90.0, 80.0, 70.0, 46.7],  '-',  'o'),
    ('DS-V4-Flash',       [93.3, 80.0, 76.7, 75.0, 46.7],  '--', 's'),
    ('DS-V4-Flash-Think', [100.0, 80.0, 76.7, 50.0, 60.0], '--', '^'),
    ('Qwen3-8B',          [100.0, 65.0, 66.7, 45.0, 33.3], '--', 'o'),
    ('Qwen3-8B-SFT',     [93.3, 85.0, 80.0, 60.0, 66.7],  '-',  'o'),
]

prop_cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']

fig, ax = plt.subplots(figsize=(8, 5.5), dpi=150)

ax.set_axisbelow(True)
ax.grid(True, linestyle='-', alpha=0.25, color='#ccc')

for i, (name, values, ls, mk) in enumerate(data):
    color = prop_cycle[i % len(prop_cycle)]
    ax.plot(x, values,
            color=color,
            marker=mk,
            linestyle=ls,
            linewidth=2.0,
            markersize=8,
            markeredgecolor='white',
            markeredgewidth=0.8,
            label=name,
            zorder=5)

ax.set_xlabel('约束数量', fontsize=13)
ax.set_ylabel('提示级准确率（%）', fontsize=13)
ax.set_xticks(x)
ax.set_xticklabels([str(i) for i in x], fontsize=12)
ax.set_yticks(range(30, 105, 10))
ax.set_ylim(28, 105)
ax.tick_params(axis='both', labelsize=11)

ax.legend(loc='lower left', fontsize=9, frameon=True,
          edgecolor='#ccc', framealpha=0.95, ncol=1,
          handlelength=2.5)

fig.patch.set_facecolor('white')
ax.set_facecolor('white')

plt.tight_layout()
plt.savefig(OUT_PATH, dpi=200, bbox_inches='tight', facecolor='white')
print(f'Saved to {OUT_PATH}')
plt.close()
