import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np
import matplotlib.patches as mp

fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 3.9),
                             gridspec_kw={'width_ratios':[1.25, 1]})

# ---- (a) the mechanism, as a signal-path cartoon --------------------------
a1.axis('off'); a1.set_xlim(0, 10); a1.set_ylim(0, 10)
def box(x, y, w, h, txt, fc, ec, fs=7.6, tc='k', bold=False):
    a1.add_patch(mp.FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.10',
                                   fc=fc, ec=ec, lw=1.0))
    a1.text(x+w/2, y+h/2, txt, ha='center', va='center', fontsize=fs, color=tc,
            fontweight='bold' if bold else 'normal')
def arrow(x0, y0, x1, y1, col='k', txt='', dy=0.22, ls='-'):
    a1.annotate('', xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle='->', color=col, lw=1.2, ls=ls))
    if txt: a1.text((x0+x1)/2, (y0+y1)/2+dy, txt, ha='center', fontsize=7, color=col)

a1.text(0.1, 9.6, 'Front wheel (GTK08, 186 264 CPR)  under  v2.0 firmware',
        fontsize=8.6, fontweight='bold')
box(0.2, 7.7, 2.0, 1.1, 'wheel turns\n1.00 rev', '#eef2f6', C['neutral'])
box(3.0, 7.7, 2.2, 1.1, 'encoder emits\n186 264 counts', '#eef2f6', C['neutral'])
box(6.1, 7.7, 3.6, 1.1, 'firmware divides by the\nshared constant 93 132',
    '#fdecea', C['defect'], tc=C['defect'])
arrow(2.25, 8.25, 2.95, 8.25)
arrow(5.25, 8.25, 6.05, 8.25)
box(6.1, 6.1, 3.6, 1.1, 'reports 2.00 rev\ni.e. double true speed',
    '#fdecea', C['defect'], tc=C['defect'], bold=True)
arrow(7.9, 7.65, 7.9, 7.25, C['defect'])
box(2.6, 4.5, 4.4, 1.1, 'PID sees overshoot, cuts PWM\nuntil the reported speed matches',
    '#fdecea', C['defect'], tc=C['defect'])
arrow(6.6, 6.05, 5.6, 5.65, C['defect'])
box(2.6, 2.9, 4.4, 1.1, 'wheel physically settles at\nHALF the commanded velocity',
    '#fdecea', C['defect'], tc=C['defect'], bold=True)
arrow(4.8, 4.45, 4.8, 4.05, C['defect'])
box(0.6, 1.1, 8.6, 1.2,
    'Rear wheels scale correctly → permanent front/rear speed split →\n'
    'the robot yaws under pure translation, with clean-looking telemetry throughout',
    '#fff4e5', C['command'], fs=7.8, tc='#7a3e00')
arrow(4.8, 2.85, 4.8, 2.35, C['defect'])
a1.set_title('(a) How one shared constant produced a silent yaw bias', loc='left')

# ---- (b) the bench cross-check that caught it -----------------------------
mot = ['FR', 'FL', 'RR', 'RL']
fwd = [119085, 115121, 57416, 57358]
rev = [118067, 115607, 58244, 59139]
x = np.arange(4); wd = 0.36
a2.bar(x-wd/2, fwd, wd, color=C['telemetry'], edgecolor='k', lw=0.5, label='forward burst')
a2.bar(x+wd/2, rev, wd, color=C['light'], edgecolor='k', lw=0.5, label='reverse burst')
a2.set_xticks(x); a2.set_xticklabels(mot)
a2.set_ylabel('raw PCNT counts, 1.5 s at PWM 110')
a2.legend(fontsize=7.4, loc='upper right')
fr_mean = np.mean(fwd[:2] + rev[:2]); rr_mean = np.mean(fwd[2:] + rev[2:])
a2.annotate('', xy=(1.75, rr_mean), xytext=(1.75, fr_mean),
            arrowprops=dict(arrowstyle='<->', color=C['fixed'], lw=1.5))
a2.text(1.68, (fr_mean+rr_mean)/2, f'ratio\n{fr_mean/rr_mean:.2f}×', ha='right',
        va='center', fontsize=8.5, color=C['fixed'], fontweight='bold')
a2.axhspan(0, 0, color='none')
a2.text(0.5, -0.30,
        'Same gearmotor, same PWM, same window.\n'
        'The ratio matches the CPR ratio exactly (2.00×),\n'
        'confirming both the wiring and the new constants.',
        transform=a2.transAxes, ha='center', va='center', fontsize=7.4, color=C['fixed'],
        bbox=dict(fc='#eaf5ea', ec=C['fixed'], lw=0.8, pad=3))
a2.set_ylim(0, 150000)
a2.set_title('(b) The bench cross-check, 4 Aug 2026', loc='left')

fig.suptitle('The dual-encoder fault. Two of the four motors carry a different encoder, and '
             'firmware through\nv2.0 applied one shared CPR constant to all four.',
             fontsize=9.5, y=1.06, x=0.02, ha='left')
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig06_encoder_cpr_fault.png'); plt.close()
print('ok')
