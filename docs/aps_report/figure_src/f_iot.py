import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg import *
import numpy as np

# ============ IoT architecture ===========================================
fig, ax = canvas(10.6, 4.9, 100, 47)
cmd, tel, grn, red = C['command'], C['telemetry'], C['fixed'], C['defect']

band(ax, 1, 1, 30, 45, 'EDGE NODE   Arduino UNO R4 WiFi')
band(ax, 34, 12.5, 27, 33.5, 'TRANSPORT   three concurrent channels',
     fc='#f4f1f8', ec=C['accent'], tc=C['accent'])
band(ax, 64, 1, 35, 45, 'LOCAL SERVER   Raspberry Pi 5, Docker (IOTstack)',
     fc='#fbf7f2', ec=cmd, tc='#7a3e00')

s1 = box(ax, 3.5, 34.5, 25, 4.6, 'SCD40   CO$_2$ / T / RH   I²C 0x62', fs=7.0)
s2 = box(ax, 3.5, 29.3, 25, 4.6, 'MPM10-AS   PM2.5 / PM10   I²C 0x4D', fs=7.0)
s3 = box(ax, 3.5, 24.1, 25, 4.6, 'MQ-135   non-selective gas   A0 / D2', fs=7.0)
s4 = box(ax, 3.5, 18.9, 25, 4.6, 'GUVA-S12SD   UV-A/UV-B   A1', fs=7.0,
         fc='#fdecea', ec=red, tc=red)
a1 = box(ax, 3.5, 11.5, 25, 4.6, 'opto-isolated relay → UV-C lamp   D9', fs=7.0,
         fc='#fdf1e3', ec=cmd)
a2 = box(ax, 3.5, 6.3, 25, 4.6, '120 mm PWM fan + tacho   D6 / D3', fs=7.0,
         fc='#fdf1e3', ec=cmd)
ax.text(16, 41.4, 'five sensors, two actuators', ha='center', fontsize=7.4,
        color=C['neutral'], style='italic')

c1 = box(ax, 36, 36.5, 23, 6.2, 'Wi-Fi → MQTT\nevery 5 s', fs=7.2,
         fc='#efe9f6', ec=C['accent'], tc=C['accent'])
c2 = box(ax, 36, 27.5, 23, 6.8, 'LoRa RYLR998 → UNO R4 Minima gateway\n'
         '30 s, ≤240 B, SF9 / BW 125 kHz / CR 4-5', fs=6.6,
         fc='#efe9f6', ec=C['accent'], tc=C['accent'])
c3 = box(ax, 36, 19.5, 23, 6.2, '4G SMS\non alert, plus every 30 min', fs=7.2,
         fc='#efe9f6', ec=C['accent'], tc=C['accent'])
ax.text(47.5, 15.6, 'run concurrently, not as a failover chain:\n'
        'detecting failure is what fails first', ha='center', fontsize=6.8,
        color=C['accent'], style='italic', linespacing=1.5)

v1 = box(ax, 66.5, 38.0, 30, 4.4, 'Mosquitto  :1883', fs=7.0)
v2 = box(ax, 66.5, 30.0, 14.2, 6.4, 'Node-RED :1880\nMQTT ingest', fs=6.8)
v3 = box(ax, 82.3, 30.0, 14.2, 6.4, 'Python LoRa\nservice v1.2', fs=6.8)
v4 = box(ax, 66.5, 22.0, 30, 5.4, 'InfluxDB 2.x :8086\none schema, both transports', fs=7.0)
v5 = box(ax, 66.5, 14.0, 30, 5.4, 'Grafana :3000\n23 panels, per-zone templating', fs=7.0)
v6 = box(ax, 66.5, 6.5, 30, 4.6, 'Flask control API  :5000', fs=7.0, fc='#fdf1e3', ec=cmd)

# sensor bus
ax.plot([31.2, 31.2], [21.0, 37.0], color=tel, lw=1.2, zorder=4)
for sb in (s1, s2, s3, s4):
    ax.plot([sb[0]+sb[2], 31.2], [sb[1]+sb[3]/2]*2, color=tel, lw=0.9, zorder=4)
for cb in (c1, c2, c3):
    arr(ax, (31.2, cb[1]+cb[3]/2), L(cb), tel, lw=1.0)
ax.plot([31.2, 31.2], [21.0, 39.6], color=tel, lw=1.2, zorder=4)

arr(ax, R(c1), (66.5, 40.2), tel)
arr(ax, R(c2), (66.5, 33.2), tel)
arr(ax, R(c3), (61.5, 22.6), tel)
ax.text(59.8, 21.2, 'to operator handset', ha='right', fontsize=6.8, color=tel)
arr(ax, (73.6, 38.0), (73.6, 36.5), tel)
arr(ax, B(v2), (73.6, 27.4), tel)
arr(ax, B(v3), (89.4, 27.4), tel)
arr(ax, B(v4), T(v5), tel)
arr(ax, L(v6), (62.5, 8.8), cmd, style='-')
arr(ax, (62.5, 8.8), (33.0, 8.8), cmd, txt='operator override, any channel',
    tdy=1.7, fs=6.8)
ax.plot([33.0, 33.0], [8.8, 13.8], color=cmd, lw=1.2)
arr(ax, (33.0, 13.8), R(a1), cmd)
arr(ax, (33.0, 8.8), R(a2), cmd)

ax.text(16, 3.4, 'The UV channel (red) is measured and displayed,\n'
        'but appears in no control path and no alert path.',
        fontsize=7.0, color=red, ha='center', va='center', linespacing=1.6)

ax.set_title('Parallel project: instrumentation and control for a UV-C air-disinfection '
             'chamber. Five sensors,\nthree concurrent wireless channels, two independent '
             'control paths, four monitored zones, no cloud dependency.',
             loc='left', fontsize=9.4, y=1.0)
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig19_iot_architecture.png'); plt.close()

# ============ IoT control law ============================================
fig, (a1x, a2x) = plt.subplots(1, 2, figsize=(9.8, 3.6),
                               gridspec_kw={'width_ratios':[1.15, 1]})
idx = np.linspace(0, 600, 1200)
fan = np.clip(128 + (255-128)*(idx-200)/300, 0, 255)
fan[idx < 200] = 0
a1x.plot(idx, fan, color=C['telemetry'], lw=2.0, label='fan PWM command')
a1x.axvspan(150, 200, color=C['command'], alpha=0.18)
a1x.text(175, 232, 'hysteresis\ndead band', ha='center', fontsize=7.2, color='#7a3e00')
a1x.axvline(150, color=C['fixed'], ls='--', lw=1.0)
a1x.axvline(200, color=C['defect'], ls='--', lw=1.0)
a1x.text(148, 40, 'lamp OFF below 150', rotation=90, ha='right', fontsize=7.0,
         color=C['fixed'])
a1x.text(203, 40, 'lamp ON above 200', rotation=90, ha='left', fontsize=7.0,
         color=C['defect'])
a1x.plot(143, 0, 'o', ms=8, color=C['fixed'], zorder=5)
a1x.annotate('dashboard capture: index 143,\nlamp correspondingly OFF',
             xy=(143, 0), xytext=(300, 60), fontsize=7.0, color=C['fixed'],
             arrowprops=dict(arrowstyle='->', color=C['fixed'], lw=0.9))
a1x.set_xlabel('MQ-135 gas index (rescaled ADC count, uncalibrated)')
a1x.set_ylabel('fan PWM (0–255)')
a1x.set_xlim(0, 600); a1x.set_ylim(0, 275)
a1x.set_title('(a) Control law as implemented', loc='left')

a2x.axis('off'); a2x.set_xlim(0,1); a2x.set_ylim(0,1)
a2x.set_title('(b) What the self-audit found', loc='left')
rows = [('UV irradiance is in no control or alert path',
         'the claimed two-input loop has one input; a dead lamp raises nothing'),
        ('off-commands do not clear AUTO',
         'an operator LIGHT OFF is reverted within one loop iteration'),
        ('MQ-135 calibration computed, stored, never used',
         'the index driving the loop is a rescaled ADC count'),
        ('GUVA-S12SD is a UV-A/UV-B part',
         'spectral mismatch at 254 nm, not a scale factor'),
        ('SMS poll busy-waits 5 s of every 10',
         'half the loop period; causes the fan RPM over-read')]
y = 0.94
for head, body in rows:
    a2x.text(0.03, y, '•  ' + head, fontsize=7.6, fontweight='bold', color=C['defect'],
             va='top', transform=a2x.transAxes)
    a2x.text(0.07, y-0.062, body, fontsize=7.2, va='top', transform=a2x.transAxes)
    y -= 0.19
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig20_iot_control_law.png'); plt.close()
print('ok')
