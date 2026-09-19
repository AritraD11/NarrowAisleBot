# -*- coding: utf-8 -*-
"""Table data and equation markup, lifted unchanged from the previous build."""
# ------------------------------------------------------------------ tables ---
TABLE_SPEC = {
    'num': '1.1',
    'title': 'The platform as built',
    'cap': ('Every figure is measured on the machine rather than taken from a data sheet, except the lidar range specification, which is the manufacturer’s and is treated in Section 1.12 as a factory acceptance condition rather than a runtime error distribution.'),
    'cols': [126.2, 327.8],
    'head': ['Item', 'Value'],
    'rows': [
        ['Footprint, tape-measured', '1.00 × 0.36 m'],
        ['Mass', '45.54 kg'],
        ['Outer and inner wheel longitudinal distance', '0.403 m and 0.333 m'],
        ['Half track width', '0.15769 m, identical for all four wheels'],
        ['Wheel radius', '0.0762 m'],
        ['Drive motors', '4 × geared DC, 24 V, 1:47 reduction, 60 rpm rated'],
        ['Encoders', 'Front pair GTK08, 186,264 counts per revolution at the wheel; '
                     'rear pair optical, 93,132'],
        ['Motor drivers', '2 × dual-channel, 20 A continuous, 1.5 V logic threshold'],
        ['Real-time controller', 'ESP32, 100 Hz control loop, hardware quadrature decoding'],
        ['Host computer', 'Raspberry Pi 5, Ubuntu 24.04, ROS 2'],
        ['Lidar', 'YDLIDAR X4 Pro, single-plane triangulation, 360°, 0.12–10 m rated '
                  'range, manufacturer-stated 2 cm absolute below 1 m and 3.5 % of '
                  'range from 1 to 6 m'],
        ['Power', 'LiFePO₄ 12.8 V, 30 Ah, with boost to 24 V drive and buck to 5 V logic'],
        ['Cargo arm and lighting', 'Two lateral and one vertical stepper axis, '
                                   'three-tube staged ultraviolet lighting'],
        ['Operating velocity limit', '0.12 m/s linear, 0.30 rad/s yaw'],
    ],
}
TABLE_IOT = {
    'num': '2.1',
    'title': 'The monitoring system as deployed',
    'cap': ('Two radio-isolated installations report to one database. The measured quantities are listed as the node reports them, which is why the gas channel appears as an index rather than as a concentration.'),
    'cols': [87.9, 366.1],
    'head': ['Item', 'Specification'],
    'rows': [
        ['Sensing node', 'Single-board microcontroller with integrated Wi-Fi'],
        ['Gateway', 'Second microcontroller with a long-range LoRa module, level-translated'],
        ['Server', 'Raspberry Pi 5, containerised data platform'],
        ['Measured quantities', 'Carbon dioxide, temperature, relative humidity, '
                                'particulate mass at two size fractions, and a '
                                'non-selective gas index'],
        ['Actuators', 'Opto-isolated relay for the lamp supply and a variable-speed fan '
                      'with tachometer feedback'],
        ['Channels', 'Local Wi-Fi at 5 s, long-range LoRa at 30 s, cellular messaging on alert'],
        ['Control law', 'Hysteresis with a dead band, with fan speed scaled across the '
                        'upper part of the index range'],
        ['Zones', 'Four, across two radio-isolated deployments against a shared database'],
    ],
}
TABLE_WHEEL = {
    'num': '1.2',
    'title': 'Per-wheel tracking error under chassis weight',
    'cap': ('Pooled over the floor drives of Section 1.10. No channel saturated at any point and no feedback channel was lost, so these figures are controller performance rather than an artefact of the drive reaching its limit.'),
    'cols': [72.4, 112.2, 164.3, 105.1],
    'head': ['Wheel', 'RMS error (rad/s)', 'Mean absolute error (rad/s)', 'Saturated samples'],
    'rows': [
        ['Front right', '0.077', '0.039', '0.0 %'],
        ['Front left', '0.066', '0.034', '0.0 %'],
        ['Rear right', '0.068', '0.032', '0.0 %'],
        ['Rear left', '0.075', '0.039', '0.0 %'],
    ],
}
TABLE_SCAN = {
    'num': '1.3',
    'title': 'Endpoint closure with and without the scan-matching front end',
    'cap': ('The same wheel data and the same scans on each row, differing only in whether the front end was applied. On every route the front end increases the endpoint error rather than reducing it.'),
    'cols': [153.1, 56.7, 106.1, 138.1],
    'head': ['Route', 'Range cap', 'Wheel odometry alone', 'With the scan-matching front end'],
    'rows': [
        ['38 s square, 1.42 m of path', '10 m', '2.58 cm', '6.2 cm'],
        ['1047 s drive, 21.85 m of wheel path', '10 m', '0.229 m, 10.53°', '0.477 m, 16.18°'],
        ['82.5 s circle, 3.193 m of path', '5 m', '16.2 mm, 0.51 %', '206.7 mm, 6.47 %'],
    ],
}
TABLES = {'TABLE_SPEC': TABLE_SPEC, 'TABLE_IOT': TABLE_IOT,
          'TABLE_WHEEL': TABLE_WHEEL, 'TABLE_SCAN': TABLE_SCAN}

# --------------------------------------------------------------- equations ---
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def mr(t, nor=False):
    pr = '<m:rPr><m:nor/></m:rPr>' if nor else ''
    t = (t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
    return (f'<m:r xmlns:m="{M}" xmlns:w="{W}">{pr}'
            f'<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'
            f'<m:t xml:space="preserve">{t}</m:t></m:r>')

def msub(base, sub):
    return f'<m:sSub xmlns:m="{M}"><m:e>{base}</m:e><m:sub>{sub}</m:sub></m:sSub>'

def mfrac(num, den, kind='bar'):
    pr = f'<m:fPr><m:type m:val="{kind}"/></m:fPr>' if kind != 'bar' else ''
    return f'<m:f xmlns:m="{M}">{pr}<m:num>{num}</m:num><m:den>{den}</m:den></m:f>'

def macc(inner, chr_='̂'):
    return (f'<m:acc xmlns:m="{M}"><m:accPr><m:chr m:val="{chr_}"/></m:accPr>'
            f'<m:e>{inner}</m:e></m:acc>')

def mdelim(inner):
    return (f'<m:d xmlns:m="{M}"><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/>'
            f'</m:dPr><m:e>{inner}</m:e></m:d>')

K = lambda s: msub(mr('K'), mr(s, nor=True))
W_ = lambda s: msub(mr('ω'), mr(s, nor=True))
D_ = lambda s: msub(mr('δ'), mr(s, nor=True))
L_ = lambda s: msub(mr('l'), mr(s, nor=True))
INV_R = mfrac(mr('1'), mr('r'), 'lin')

EQ1 = (K('o') + mr('=') + L_('1') + mr('+') + mr('d') + mr('=') + mr('0.5607')
       + mr(' m, ', nor=True)
       + K('i') + mr('=') + L_('2') + mr('+') + mr('d') + mr('=') + mr('0.4907')
       + mr(' m', nor=True))

def _wheel(name, a, b, c, kk):
    return (W_(name) + mr('=') + INV_R
            + mdelim(mr('u') + mr(a) + mr('v') + mr(b) + mr('ω') + K(kk)))

EQ2A = (_wheel('FR', '+', '+', None, 'o') + mr(', ', nor=True)
        + _wheel('FL', '−', '−', None, 'i') + mr(',', nor=True))
EQ2B = (_wheel('RR', '−', '+', None, 'i') + mr(', ', nor=True)
        + _wheel('RL', '+', '−', None, 'o') + mr('.', nor=True))

EQ3 = (macc(mr('ω')) + msub(mr(''), mr('outer', nor=True)).replace('<m:e></m:e>', '<m:e></m:e>')
       if False else
       (msub(macc(mr('ω')), mr('outer', nor=True)) + mr('=')
        + mfrac(mr('r') + mdelim(W_('FR') + mr('−') + W_('RL')), mr('2') + K('o'))
        + mr(', ', nor=True)
        + msub(macc(mr('ω')), mr('inner', nor=True)) + mr('=')
        + mfrac(mr('r') + mdelim(W_('RR') + mr('−') + W_('FL')), mr('2') + K('i'))))

EQ4 = (msub(mr('e'), mr('ω')) + mr('=') + mfrac(mr('r'), mr('2'))
       + mdelim(mfrac(D_('outer'), K('o')) + mr('−') + mfrac(D_('inner'), K('i'))))

EQS = {'EQ1': [EQ1], 'EQ2': [EQ2A, EQ2B], 'EQ3': [EQ3], 'EQ4': [EQ4]}

