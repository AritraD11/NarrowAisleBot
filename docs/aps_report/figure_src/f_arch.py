import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg import *

fig, ax = canvas(11.4, 7.8, 100, 77)
cmd, tel = C['command'], C['telemetry']

band(ax, 1, 42.0, 98, 33.0,
     'PLANNING & PERCEPTION    Raspberry Pi 5 · Ubuntu 24.04 · ROS 2 Jazzy    soft real time, 10–20 Hz')
band(ax, 1, 22.0, 98, 17.5,
     'REAL-TIME CONTROL    ESP32-WROOM-32 · FreeRTOS dual core    hard real time, 100 Hz',
     fc='#f4f1f8', ec=C['accent'], tc=C['accent'])
band(ax, 1, 1.0, 98, 19.0, 'ACTUATION, SENSING & POWER',
     fc='#fbf7f2', ec=C['command'], tc='#7a3e00')

# ---- Pi: operator column -------------------------------------------------
b_dash = box(ax, 3.5, 56.5, 16, 7.0, 'phone_dashboard\nFastAPI :8080\nMap button + CSV log', fs=6.7)
b_tel  = box(ax, 3.5, 47.5, 16, 6.0, 'joy_to_aislebot\nkeyboard_teleop', fs=6.7)
b_arm  = box(ax, 3.5, 42.8, 16, 3.6, 'arm_bridge', fs=6.7)

# ---- Pi: kinematics + bridge --------------------------------------------
b_ik   = box(ax, 23, 52.0, 15, 7.4, 'mecanum_teleop\n_asymmetric\nasymmetric IK', fs=6.7,
             fc='#e6eef6', ec=tel, tc=tel)
b_br   = box(ax, 42, 52.0, 14, 7.4, 'esp32_bridge\n<V,fr,fl,rr,rl>\n20 Hz', fs=6.7)
b_odo  = box(ax, 42, 62.5, 14, 5.4, 'odometry_publisher\n/wheel_odom\n+ TF odom→base_link', fs=6.4)

# ---- Pi: perception ------------------------------------------------------
b_rel  = box(ax, 60.5, 44.5, 16, 6.4, 'scan_relay\nQoS bridge +\nscan re-indexing', fs=6.7,
             fc='#e6eef6', ec=tel, tc=tel)
b_slam = box(ax, 60.5, 54.5, 16, 7.4, 'slam_toolbox\nonline async\npose graph + /map', fs=6.7,
             fc='#e6eef6', ec=tel, tc=tel)
b_fox  = box(ax, 60.5, 64.5, 16, 4.0, 'foxglove_bridge :8765', fs=6.5)
b_nav  = box(ax, 81, 50.0, 15.5, 11.0, 'Nav2\nplanner_server (A*)\ncontroller_server (DWB)\n\n'
             'configured and\naudited, not yet run', fs=6.7,
             fc='white', ec=C['grey'], ls='--', tc=C['neutral'])

# ---- ESP32 ---------------------------------------------------------------
b_core0 = box(ax, 14, 23.5, 21, 12.0,
              'Core 0 — serial and safety\n\nframe parse · telemetry 20 Hz\n'
              'command watchdog 750 ms\noverspeed / runaway / stall trips\nlatching E-STOP',
              fs=6.7, fc='#efe9f6', ec=C['accent'], tc=C['accent'])
b_pid   = box(ax, 40, 23.5, 20, 12.0,
              'Core 1 — PID task, 100 Hz\n\n'
              r'$pwm = K_{ff}\,\omega + K_{stat}\,\mathrm{sgn}(\omega)$' + '\n'
              r'$\qquad +\, K_p e + K_i \int\! e\,dt - K_d \dot{y}$' + '\n\n'
              'dynamic anti-windup · slew limit',
              fs=6.7, fc='#efe9f6', ec=C['accent'], tc=C['accent'])
b_pcnt  = box(ax, 65, 25.5, 17, 8.0, 'PCNT peripheral\nfour-channel hardware\nquadrature decode\n'
              'zero CPU cost', fs=6.7, fc='#efe9f6', ec=C['accent'], tc=C['accent'])

# ---- hardware ------------------------------------------------------------
b_lcd  = box(ax, 3.5, 11.0, 10, 5.4, '16×2 I²C LCD\n0x27', fs=6.7, fc='#fdf1e3', ec=cmd)
b_mega = box(ax, 15.5, 11.0, 19.5, 5.4, 'Arduino Mega 2560\narm steppers + 3-tube\nstaged UV-C (v8)',
             fs=6.7, fc='#fdf1e3', ec=cmd)
b_mdd  = box(ax, 40, 11.0, 20, 5.4, '2 × Cytron MDD20A\nPWM 5 kHz + DIR', fs=6.7,
             fc='#fdf1e3', ec=cmd)
b_mot  = box(ax, 40, 3.0, 20, 6.0, '4 × Rhino RMCS-2086\n24 V · 1:47 · 60 RPM\nDekuPro 6" mecanum',
             fs=6.7, fc='#fdf1e3', ec=cmd)
b_enc  = box(ax, 65, 11.0, 17, 5.6, 'encoders\nFR/FL GTK08 186 264 CPR\nRR/RL optical 93 132 CPR',
             fs=6.2, fc='#fdf1e3', ec=cmd)
b_lvl  = box(ax, 65, 3.0, 17, 5.6, '8-channel BSS138\nlevel shifter\n5 V → 3.3 V', fs=6.7,
             fc='#fdf1e3', ec=cmd)
b_lid  = box(ax, 84.5, 11.0, 13, 5.6, 'YDLIDAR X4 Pro\n~1258 pts @ 11.5 Hz', fs=6.5,
             fc='#fdf1e3', ec=cmd)
b_pwr  = box(ax, 3.5, 3.0, 31.5, 5.6,
             'LiFePO$_4$ 12.8 V / 30 Ah  →  boost 24 V (drive)  ·  buck 5 V (logic)\n'
             'SSR-50DD bus disconnect   ·   DS3231 RTC on the shared I²C bus',
             fs=6.3, fc='#fdf1e3', ec=cmd)

# ---- command path --------------------------------------------------------
arr(ax, R(b_dash), (23, 57.5), cmd, txt='/cmd_vel', tdy=1.2)
arr(ax, R(b_tel),  (23, 54.5), cmd)
arr(ax, R(b_ik), L(b_br), cmd, txt='/wheel_speeds', tdy=1.3)
arr(ax, B(b_br), (49, 35.5), cmd, txt='USB serial 921600', tdy=4.5, tdx=-4.5)
arr(ax, B(b_pid), T(b_mdd), cmd, txt='signed PWM + DIR', tdy=0, tdx=13.0)
arr(ax, B(b_mdd), T(b_mot), cmd, txt='24 V', tdy=0, tdx=3.0)
arr(ax, B(b_arm), (11.5, 16.9), cmd, txt='/dev/mega\n115200', tdy=0, tdx=-6.5, rad=-0.10)

# ---- telemetry path ------------------------------------------------------
arr(ax, R(b_mot), L(b_lvl), tel, rad=-0.15)
arr(ax, T(b_lvl), B(b_enc), tel, txt='A/B 5 V', tdy=0, tdx=3.4)
arr(ax, T(b_enc), B(b_pcnt), tel, txt='3.3 V quadrature', tdy=0, tdx=-8.5)
arr(ax, L(b_pcnt), R(b_pid), tel, txt='rad/s', tdy=1.2)
arr(ax, (52.5, 35.5), (52.5, 52.0), tel, txt='13-column CSV, 20 Hz', tdy=-4.5, tdx=-1.0)
arr(ax, T(b_br), B(b_odo), tel)
arr(ax, T(b_lid), (91.0, 40.0), tel, txt='/scan\nbest-effort', tdy=0, tdx=7.0)
arr(ax, (91.0, 40.0), (78.5, 40.0), tel, style='-')
arr(ax, (78.5, 40.0), (78.5, 47.7), tel, style='-')
arr(ax, (78.5, 47.7), R(b_rel), tel)
arr(ax, T(b_rel), B(b_slam), tel, txt='/scan_reliable', tdy=0, tdx=8.0)
arr(ax, R(b_odo), (81, 59.0), tel, txt='TF', tdy=1.4, tdx=6)
arr(ax, R(b_slam), (81, 56.0), tel, txt='/map', tdy=1.2)
arr(ax, T(b_slam), B(b_fox), tel)
arr(ax, (60.5, 66.5), (56.0, 66.5), tel, rad=0.0)

# ---- future closure ------------------------------------------------------
arr(ax, T(b_nav), (88.75, 70.5), C['grey'], ls='--', style='-')
arr(ax, (88.75, 70.5), (30.5, 70.5), C['grey'], ls='--', style='-',
    txt='not yet closed: /cmd_vel from the planner back into the same asymmetric IK',
    tdy=1.6, tc=C['neutral'], fs=7.2)
arr(ax, (30.5, 70.5), T(b_ik), C['grey'], ls='--')

ax.plot([], [], color=cmd, lw=1.6, label='command path')
ax.plot([], [], color=tel, lw=1.6, label='telemetry and perception path')
ax.plot([], [], color=C['grey'], lw=1.4, ls='--', label='configured, not yet exercised')
ax.legend(loc='upper left', bbox_to_anchor=(0.0, -0.005), ncol=3, fontsize=7.6)

plt.tight_layout()
plt.savefig(f'{FIGDIR}/fig02_system_architecture.png')
print('ok')
