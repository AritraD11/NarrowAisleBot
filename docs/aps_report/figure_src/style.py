import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams['font.family'] = 'DejaVu Sans'
rcParams['font.size'] = 9
rcParams['axes.titlesize'] = 10
rcParams['axes.labelsize'] = 9
rcParams['axes.grid'] = True
rcParams['grid.alpha'] = 0.25
rcParams['grid.linewidth'] = 0.6
rcParams['axes.spines.top'] = False
rcParams['axes.spines.right'] = False
rcParams['legend.frameon'] = False
rcParams['legend.fontsize'] = 8
rcParams['figure.dpi'] = 200
rcParams['savefig.dpi'] = 300
rcParams['savefig.bbox'] = 'tight'
rcParams['savefig.pad_inches'] = 0.12

# consistent colour language across the whole report
C = dict(
    telemetry = '#1f4e79',   # data / measurement
    command   = '#c55a11',   # command / setpoint
    defect    = '#c00000',   # defect, gap, failure
    fixed     = '#2e7d32',   # resolved / validated
    neutral   = '#5a5a5a',
    light     = '#b7c9d9',
    accent    = '#7030a0',
    grey      = '#9e9e9e',
)
MOT = ['FR','FL','RR','RL']
MOTC = ['#1f4e79','#2e75b6','#c55a11','#e8a33d']
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
FIGDIR = _os.path.join(_os.path.dirname(_HERE), 'figures')
REPO   = _os.path.dirname(_os.path.dirname(_os.path.dirname(_HERE)))
