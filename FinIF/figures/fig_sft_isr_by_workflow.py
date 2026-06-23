"""SFT ISR by Workflow: Qwen3.5-4B vs Qwen3.5-4B-SFT — 5 workflows + Overall | Quality."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# ── Data ──
workflows = ['Intake', 'Resear.', 'Decis.', 'Risk/Comp.', 'Execu.', 'Overall']
base_isr = [0.00, 1.64, 1.64, 0.00, 0.00, 0.65]
sft_isr  = [21.31, 27.87, 18.03, 17.74, 29.03, 22.80]

base_quality = 3.82
sft_quality  = 5.77

# ── Positions ──
x_isr = np.arange(6).astype(float)
x_qual = 6.15
width = 0.38

# figsize ≈ ACL \textwidth so PDF embeds ~1:1
fig, ax_l = plt.subplots(figsize=(6.3, 3.2))
ax_r = ax_l.twinx()

# ── Vertical separator (dashed, bold) ──
ax_l.axvline(x=5.5, color='#888', linestyle='--', linewidth=1.8, zorder=0)

# Colors
c_base = '#A0C4E8'
c_base_edge = '#7BA8D4'
c_sft = '#F0B86C'
c_sft_edge = '#D49840'

# ── ISR bars (left axis) ──
ax_l.bar(x_isr - width/2, base_isr, width,
         color=c_base, edgecolor=c_base_edge, linewidth=0.6, zorder=2)
ax_l.bar(x_isr + width/2, sft_isr, width,
         color=c_sft, edgecolor=c_sft_edge, linewidth=0.6, zorder=2)

for i, v in enumerate(base_isr):
    label_y = 0.8 if v == 0 else v + 0.5
    ax_l.text(x_isr[i] - width/2, label_y, f'{v:.1f}', ha='center', va='bottom',
              fontsize=9, fontweight='bold', color='#444')
for i, v in enumerate(sft_isr):
    ax_l.text(x_isr[i] + width/2, v + 0.5, f'{v:.1f}', ha='center', va='bottom',
              fontsize=9, fontweight='bold', color='#444')

# ── Quality bars (right axis) ──
ax_r.bar(x_qual - width/2, base_quality, width,
         color=c_base, edgecolor=c_base_edge, linewidth=0.6, zorder=2)
ax_r.bar(x_qual + width/2, sft_quality, width,
         color=c_sft, edgecolor=c_sft_edge, linewidth=0.6, zorder=2)

ax_r.text(x_qual - width/2 - 0.08, base_quality + 0.25, f'{base_quality:.2f}',
          ha='center', va='bottom', fontsize=9, fontweight='bold', color='#444')
ax_r.text(x_qual + width/2, sft_quality + 0.15, f'{sft_quality:.2f}',
          ha='center', va='bottom', fontsize=9, fontweight='bold', color='#444')

# ── Axes styling ──
ax_l.set_ylabel('ISR (%)', fontsize=11)
ax_l.set_ylim(0, 36)
ax_r.set_ylabel('Quality (0–10)', fontsize=11)
ax_r.set_ylim(0, 10)

all_x = list(x_isr) + [x_qual]
all_labels = workflows + ['Quality']
ax_l.set_xticks(all_x)
ax_l.set_xticklabels(all_labels, fontsize=10)
# Bold "Overall" and "Quality" labels
for label in ax_l.get_xticklabels():
    if label.get_text() in ('Overall', 'Quality'):
        label.set_fontweight('bold')
ax_l.set_xlim(-0.55, 6.8)

ax_l.tick_params(axis='y', labelsize=9.5)
ax_r.tick_params(axis='y', labelsize=9.5)

ax_l.spines['top'].set_visible(False)
ax_r.spines['top'].set_visible(False)
ax_l.grid(axis='y', alpha=0.25, linestyle='--', zorder=0)

# ── Legend ──
ax_l.legend(
    handles=[plt.Rectangle((0, 0), 1, 1, facecolor=c_base, edgecolor=c_base_edge),
             plt.Rectangle((0, 0), 1, 1, facecolor=c_sft, edgecolor=c_sft_edge)],
    labels=['Qwen3.5-4B', 'Qwen3.5-4B-SFT'],
    fontsize=9.5, loc='upper left', ncol=2, framealpha=0.9)

plt.tight_layout()
plt.savefig('../pdf/sft_isr_by_workflow.pdf', bbox_inches='tight', dpi=300)
print('Saved')
