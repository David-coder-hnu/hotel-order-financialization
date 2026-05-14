"""
Generate 3 publication-quality figures for flight FSR paper.
"""
import json, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from pathlib import Path

OUT = Path(r"C:\Users\weida\Desktop\酒店研究\output\paper_figures")
OUT.mkdir(exist_ok=True)

plt.rcParams.update({
    'font.size': 11, 'axes.titlesize': 13, 'axes.labelsize': 12,
    'legend.fontsize': 9, 'figure.dpi': 150,
    'font.family': 'serif', 'pdf.fonttype': 42, 'ps.fonttype': 42,
})

with open(OUT.parent / 'flight_fsr_results_v1.json') as f:
    results = json.load(f)

# ════════════════════════════════════
# Figure 1: Copula Sensitivity
# ════════════════════════════════════
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))
labels = ['Gaussian\n(ν→∞)', 't(6)', 't(4)']
el_vals = [28, 25, 26]
var99_vals = [4.6, 5.3, 6.2]
colors = ['#2196F3', '#4CAF50', '#FF9800']

b1 = ax1.bar(labels, el_vals, color=colors, edgecolor='white', lw=0.8)
ax1.set_ylabel('Senior EL (bps)'); ax1.set_title('Expected Loss: Near-Invariant')
ax1.axhline(y=50, color='red', ls='--', lw=0.8, label='A threshold (50 bps)')
ax1.legend(fontsize=8)
for bar, v in zip(b1, el_vals):
    ax1.text(bar.get_x() + bar.get_width()/2, v + 1, f'{v}', ha='center', fontweight='bold')

b2 = ax2.bar(labels, var99_vals, color=colors, edgecolor='white', lw=0.8)
ax2.set_ylabel('Senior VaR 99% (%)'); ax2.set_title('Tail Risk: Visible in VaR 99%')
ax2.axhline(y=8.0, color='red', ls='--', lw=0.8, label='A threshold (8%)')
ax2.legend(fontsize=8)
for bar, v in zip(b2, var99_vals):
    ax2.text(bar.get_x() + bar.get_width()/2, v + 0.3, f'{v}%', ha='center', fontweight='bold')

fig.suptitle('Figure 1: Copula Sensitivity — Expected Loss vs. Tail Risk', fontweight='bold', y=1.02)
plt.tight_layout()
fig.savefig(OUT / 'fig1_copula_sensitivity.pdf', bbox_inches='tight')
fig.savefig(OUT / 'fig1_copula_sensitivity.png', bbox_inches='tight')
plt.close(); print("Fig1 saved")

# ════════════════════════════════════
# Figure 2: Carrier PD Distribution
# ════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 5.5))
cd = sorted(results.get('carrier_credit', []), key=lambda x: -x.get('pd_calibrated', 0))
names = [c['carrier'] for c in cd]
pds = [c['pd_calibrated'] * 100 for c in cd]
types = [c.get('carrier_type', 'other') for c in cd]
tcolors = {'major': '#1565C0', 'lcc': '#E65100', 'regional': '#2E7D32', 'other': '#757575'}

bars = ax.barh(range(len(names)), pds, color=[tcolors.get(t, '#757575') for t in types],
               edgecolor='white', lw=0.5)
ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=9, family='monospace')
ax.set_xlabel('Calibrated Annual PD (%)'); ax.invert_yaxis()
for i, (v, t) in enumerate(zip(pds, types)):
    ax.text(v + 0.2, i, f'{v:.2f}%', va='center', fontsize=7.5)

legend_elements = [Patch(facecolor=tcolors[t], label=t.capitalize()) for t in ['major', 'lcc', 'regional', 'other']]
ax.legend(handles=legend_elements, loc='lower right', fontsize=9, title='Carrier Type')
ax.axvline(x=0.76, color='black', ls='--', lw=0.8)
ax.text(0.9, 21, 'Pool PD = 0.76%', fontsize=8, fontstyle='italic')
ax.set_title('Figure 2: Calibrated Carrier Default Probabilities by Type', fontweight='bold')
plt.tight_layout()
fig.savefig(OUT / 'fig2_carrier_pd.pdf', bbox_inches='tight')
fig.savefig(OUT / 'fig2_carrier_pd.png', bbox_inches='tight')
plt.close(); print("Fig2 saved")

# ════════════════════════════════════
# Figure 3: Booking Curve Sensitivity
# ════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 5))
bcs = results.get('booking_curve_sensitivity', [])
betas = [b['beta'] for b in bcs]
carrier_pos = [b['carrier_discount_pct'] for b in bcs]  # JSON has this
user_save = [b['user_saving_pct'] for b in bcs]
fwd_prem = [b['forward_premium_pct'] for b in bcs]

bar_colors = ['#4CAF50' if v >= 0 else '#F44336' for v in carrier_pos]
ax.bar(betas, carrier_pos, width=0.012, color=bar_colors, edgecolor='white', lw=0.5)
ax.axhline(y=0, color='black', lw=0.8)
ax.set_xlabel('Booking Curve Parameter β'); ax.set_ylabel('Carrier Revenue Position (%)')

ax2 = ax.twinx()
ax2.plot(betas, user_save, 'o-', color='#2196F3', lw=2, ms=9, label='User Saving (%)')
ax2.set_ylabel('User Saving (%)', color='#2196F3'); ax2.tick_params(axis='y', labelcolor='#2196F3')
ax2.set_ylim(0, 40)

for b, fp in zip(betas, fwd_prem):
    idx = betas.index(b)
    ax.annotate(f'Fwd prem: {fp:.0f}%', (b, carrier_pos[idx]),
                xytext=(0, 14 if carrier_pos[idx] >= 0 else -22),
                textcoords='offset points', ha='center', fontsize=7, color='gray')

ax.axvline(x=0.22, color='black', ls=':', lw=1.5, alpha=0.5)
ax.text(0.22, max(carrier_pos) + 1, 'Baseline\nβ=0.22', ha='center', fontsize=8, fontweight='bold')
ax2.legend(loc='lower left', fontsize=9)
ax.set_title('Figure 3: Booking Curve Sensitivity — Carrier Position vs. User Saving', fontweight='bold')
plt.tight_layout()
fig.savefig(OUT / 'fig3_booking_curve.pdf', bbox_inches='tight')
fig.savefig(OUT / 'fig3_booking_curve.png', bbox_inches='tight')
plt.close(); print("Fig3 saved")

print(f"\nDone. 3 figures in {OUT}/")
