import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import matplotlib.patches as mp

def canvas(w, h, xlim=100, ylim=100):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, xlim); ax.set_ylim(0, ylim); ax.axis('off')
    ax.set_aspect('auto')
    return fig, ax

def box(ax, x, y, w, h, txt, fc='#eef2f6', ec=None, tc='k', fs=7.4, bold=False,
        style='round,pad=0.6', lw=1.0, ls='-', zorder=3, va='center'):
    ec = ec or C['neutral']
    ax.add_patch(mp.FancyBboxPatch((x, y), w, h, boxstyle=style, fc=fc, ec=ec,
                                   lw=lw, ls=ls, zorder=zorder))
    ax.text(x+w/2, y+h/2, txt, ha='center', va=va, fontsize=fs, color=tc,
            fontweight='bold' if bold else 'normal', zorder=zorder+1,
            linespacing=1.35)
    return (x, y, w, h)

def band(ax, x, y, w, h, title, fc='#f7f9fb', ec=None, fs=8.2, tc=None):
    ec = ec or C['grey']; tc = tc or C['neutral']
    ax.add_patch(mp.FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.8', fc=fc,
                                   ec=ec, lw=1.0, ls='--', zorder=1))
    ax.text(x+1.6, y+h-1.6, title, ha='left', va='top', fontsize=fs,
            color=tc, fontweight='bold', zorder=2)

def arr(ax, p0, p1, col=None, lw=1.2, ls='-', txt='', fs=6.8, tdy=1.4, tdx=0,
        rad=0.0, style='->', tc=None, zorder=5, ha='center'):
    col = col or C['neutral']; tc = tc or col
    ax.annotate('', xy=p1, xytext=p0, zorder=zorder,
                arrowprops=dict(arrowstyle=style, color=col, lw=lw, ls=ls,
                                connectionstyle=f'arc3,rad={rad}',
                                shrinkA=1.5, shrinkB=1.5))
    if txt:
        ax.text((p0[0]+p1[0])/2+tdx, (p0[1]+p1[1])/2+tdy, txt, ha=ha, va='center',
                fontsize=fs, color=tc, zorder=zorder+1, linespacing=1.3)

def R(b):   return (b[0]+b[2], b[1]+b[3]/2)
def L(b):   return (b[0], b[1]+b[3]/2)
def T(b):   return (b[0]+b[2]/2, b[1]+b[3])
def B(b):   return (b[0]+b[2]/2, b[1])
def C_(b):  return (b[0]+b[2]/2, b[1]+b[3]/2)
