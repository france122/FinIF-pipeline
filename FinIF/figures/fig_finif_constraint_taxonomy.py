"""FinIF-test constraint taxonomy donut chart."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "pdf" / "finif_constraint_taxonomy.pdf"

labels = ['Format &\nPresentation', 'Decision &\nBoundary',
          'Evidence &\nGrounding', 'Quantitative\nVerification']
sizes = [44.3, 22.7, 20.8, 12.1]
colors = ['#4A8BCF', '#D07062', '#B0D8F0', '#F5C0A0']
explode = (0.03, 0.03, 0.03, 0.03)

fig, ax = plt.subplots(figsize=(6, 6))

wedges, texts, autotexts = ax.pie(
    sizes, labels=None, autopct='%1.1f%%', startangle=90,
    colors=colors, pctdistance=0.78, explode=explode, radius=1.15,
    wedgeprops=dict(width=0.48, edgecolor='white', linewidth=2.5),
    textprops=dict(fontsize=14, fontweight='bold')
)

for t in autotexts:
    t.set_color('#222')

ax.text(0, 0, 'FinIF-test', ha='center', va='center',
        fontsize=22, fontweight='bold', fontstyle='italic')

fig.legend(wedges, [l.replace('\n', ' ') for l in labels],
           loc='lower center', ncol=2, fontsize=18,
           frameon=True, framealpha=0.9, edgecolor='#ccc',
           handletextpad=0.6, columnspacing=1.5,
           markerscale=1.5, borderpad=1.0)

fig.subplots_adjust(bottom=0.22)
fig.savefig(OUT, bbox_inches='tight', dpi=300)
print(f'Saved: {OUT}')
