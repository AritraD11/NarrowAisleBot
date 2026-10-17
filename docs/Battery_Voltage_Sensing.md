# Battery voltage on the Pi: can the old LCD meter do it?

17 Oct 2026. Planning only. Nothing is wired yet, and every component value
below that comes from a photo is a reading of blurry silkscreen until Step 1
confirms it on the bench. Predictions are written down before the
measurements, same as every other test in this repo.

The question, in the operator's words: the little LCD battery meter that
used to sit across the 12.8 V pack (wired straight onto the terminals, in
parallel with everything else) already steps 12 V down and reads it. Can it
be modified, with some extra parts, so the Pi reads the voltage directly?

Short answer: yes, three different ways, and one of them is a decent
engineering exercise. None of them beats putting the INA226 that
`Hardware_Roadmap.md` §2 already calls for across the same two terminals.
The reasoning is below, followed by the steps.

---

## 1. What the board is

The PCB says **GuYu GY-6 V6.50**, dated 20250525. No listing or datasheet
turned up under that name, so this section is read off the two photos.

| Ref | Marking | Best reading | Confidence |
|---|---|---|---|
| U2 | ground off, TSSOP-20 | The microcontroller. The `V D C G` pads right above it are its 2-wire programming port (VCC, data, clock, GND). | fairly sure |
| U4 | unreadable, SSOP-24 | Segment LCD driver, HT1621B-style, sitting right beside the glass's pins | guess |
| Q1 | Wayon logo, `…2N60`, DPAK | 600 V, ~2 A N-channel MOSFET | sure of the class |
| D1 | `M7`, SMA | 1N4007 equivalent (1 A, 1000 V) | sure |
| 2 resistors | `30E` | 2.00 MΩ each (EIA-96 code: 30 = 200, E = ×10⁴) | likely |
| 1 resistor next to them | `01D`, blurry | 100 kΩ (01 = 100, D = ×10³) | unsure |
| others | `106`, `200`, `102` | 10 MΩ, 20 Ω, 1 kΩ | likely |
| SOT-23s | `30H`, `SA` | can't identify from markings; regulator and transistor would be guesses | none |
| header | `V G R T O` | power, ground, probably a UART's RX and TX, plus one extra pin | labels only |

The front is a bare segment LCD (pins soldered through at both ends) with
two buttons, K11 and K21. It can only light the digits and icons built into
the glass.

Put together, this looks like the usual wide-input battery meter, the kind
sold as "8 to 100 V" or similar. Two resistors of 2 MΩ in series feed
100 kΩ, which divides by about 41 (100 k / 4.1 M = 0.0244). With a 3.3 V ADC
that puts full scale near 135 V, which fits a meter meant for anything up to
a 100 V pack. The series pair is there because a single small chip resistor
is only rated for 150 to 200 V across it, so high-voltage dividers split the
top leg.

The 600 V MOSFET is the odd part on a meter that lives on 12 V. Two
readings fit:

1. It's a linear pre-regulator. Wide-input meters often drop the battery
   down to something an ordinary regulator can survive by running a
   high-voltage MOSFET as a source follower with a zener on its gate. A
   10 MΩ (`106`) gate bias resistor would fit that. The 600 V rating is
   overkill at 13 V but those parts cost almost nothing.
2. It's a switched output (a low-voltage alarm or cut-off) driving whatever
   plugs into the yellow 2-pin connector.

Which one depends on which connector went to the battery. If the yellow
JST was the battery lead, (1) is the better bet. Step 1 settles it.

**About the percentage it showed.** These meters usually have a battery-type
setting behind the two buttons. If it was left on a 12 V lead-acid profile
(full is about 12.7 V, empty about 11.8 V), then a LiFePO4 pack resting at
13.0 V, which is only about a third full, would still read 100%. If the
meter sat at 100% for most of a run, that's probably why. I don't know
which setting it was on.

---

## 2. What the Pi is actually missing

The Pi 5 has no analog input at all. Whatever route gets chosen, it ends at
a chip that turns volts into a number and talks I²C (or UART) to the Pi.

That changes how to look at the meter. The step-down part, the thing it
seemed to already do, is the cheapest part of the whole problem: two
resistors. The valuable part is the ADC plus its calibration, and on this
board that sits inside a microcontroller whose markings were ground off,
which usually comes with locked firmware too. So "reusing the meter" can
only mean one of three things:

- grab the analog signal before the microcontroller sees it (Route A),
- get the number out of the microcontroller over its serial pins (Route B),
- or snoop on what it sends to the LCD driver (Route C).

---

## 3. The accuracy bar this pack sets

The pack is the SM12830SL LiFePO4, 12.8 V nominal, 30 Ah
(`Master_Reference.md` §2.5). Its flat discharge curve is the whole reason
`Hardware_Roadmap.md` §2 says voltage-to-percent is bad, so here's the
quantitative version.

Approximate resting voltage for a 4-cell LiFePO4 pack (rested an hour or
more, around 25 °C). Published tables disagree by about 50 mV, and this
particular pack's curve hasn't been measured:

| State of charge | Resting voltage, 4S |
|---|---|
| 100% (just off the charger, settling) | 13.4 to 13.6 V |
| 90% | ~13.3 to 13.4 V |
| 70% | ~13.2 V |
| 50% | ~13.05 to 13.15 V |
| 30% | ~12.9 to 13.0 V |
| 20% | ~12.8 to 12.9 V |
| 10% | 12.0 to 12.8 V (the knee) |
| 0% | ~10 to 11 V (BMS cut-off territory) |

So 20% to 90% fits inside roughly 0.4 to 0.6 V. Through the middle third of
the pack it's closer to 5 mV per percent. A reading that's off by 20 mV is
about 4% of charge at rest. One that's off by 100 mV is about 20%, and at
that point the number is decoration.

And that's at rest. While driving, the pack sags by its current times its
internal resistance plus the wiring's, which on a pack like this is a few
tens of milliohms (not measured here). At 10 A that's a few hundred
millivolts, bigger than the whole flat region. Voltage alone can't give a
believable percentage while the robot is moving. That's the argument for
measuring current as well, and it holds whichever ADC does the voltage.

**Correction to `Hardware_Roadmap.md` §2.2.** It says "roughly 13.0 V near
empty, 14.6 V near full" for the OCV table. 14.6 V is the charger's cut-off
voltage, only present while a charger is pushing current in. A rested full
pack sits near 13.4 V, and 13.0 V at rest is roughly a third full, not
empty. Any OCV correction built on the old numbers would read badly wrong.

---

## 4. The four routes

### Route A: tap the meter's divider, buffer it, digitise it

This is the "add some components" version, and it does work.

The tap is the junction where the 100 kΩ meets the 2 MΩ chain, about
0.32 V at 13.2 V. Why not run it straight into an ADC? Because that node
has about 98 kΩ of source impedance. The ADS1115's input is a switched
capacitor, and TI's table for the family (checked in the ADS1115L sheet)
puts its effective differential input impedance at about 710 kΩ on the
±0.512 V range. Hooked up directly, the reading comes
out about 12% low, and the meter's own display drops by the same amount
because both are looking at the same loaded node. So it needs a buffer.

```
METER BOARD (existing)                        ADDED (small perfboard glued beside the meter)

BAT+ --fuse--[1N4007?]-- 2.00M -- 2.00M --+-- VSENSE (~0.32 V) --> meter's MCU
                                          |
                                         100k    + 100nF across it (VSENSE to meter G)
                                          |
BAT- ---------------------------- meter G +----------------------------------+
                                                                             | sense-ground wire
VSENSE -- 100k --> (+) MCP6002 voltage follower, powered from Pi 3V3 / GND   |
                       out -- 100R --+--> ADS1115 AIN0                       |
                                    10nF                                     |
                                     +--> ADS1115 AIN1 <---------------------+

ADS1115: VDD = Pi 3V3 (pin 1), GND = Pi GND (pin 6), SDA = pin 3, SCL = pin 5,
         ADDR to GND -> I2C address 0x48 (free: bus already has 0x27, 0x68)
```

What each added part is for:

- The 100 nF across the bottom resistor makes a ~16 Hz low-pass with the
  98 kΩ source, which knocks down motor PWM pickup on that high-impedance
  node and gives the meter's own ADC a steadier input.
- The 100 kΩ in series with the op-amp input costs nothing in accuracy
  (CMOS input current is picoamps). It stops the meter, which is always on,
  from pushing current into the op-amp's protection diodes when the Pi and
  the op-amp are off.
- MCP6002 because its inputs and output reach the rails and it runs on
  3.3 V. An LM358 will do in a pinch, since 0.32 V is inside its input range
  at 3.3 V, but it's at the bottom of its supply rating.
- Measuring AIN0 against AIN1, with AIN1 on its own wire back to the
  meter's ground, makes the reading ignore any offset between the meter's
  ground and the Pi's. With motor return current flowing in shared ground
  wiring, that offset isn't zero.
- Keep the 98 kΩ node short. The buffer goes right at the meter, and only
  the low-impedance buffered signal travels to the ADS1115.

ADS1115 setting: single-shot, AIN0 minus AIN1, ±0.512 V range, 8 samples/s.
That's config word `0x8903`. One count is 15.6 µV, about 0.64 mV at the
battery after the ×41.

**The catch is that the ×41 also multiplies every error after the divider.**

| Error source | Before calibration | After 2-point calibration |
|---|---|---|
| Divider ratio (assuming 1% parts) | up to ±2%, about ±260 mV | gone |
| Op-amp offset (MCP6002, ±4.5 mV max, ×41) | up to ±185 mV | gone |
| Divider temperature drift (thick film, assume up to 200 ppm/°C mismatch) | | up to ±26 mV per 10 °C |
| Op-amp offset drift (~2 µV/°C, ×41) | | ~1 mV per 10 °C |
| **If the divider sits after the 1N4007** | 0.6 to 0.7 V low | fixed part gone; the drop still moves about 2 mV/°C and with the meter's current draw |

Uncalibrated, Route A is useless on this pack. Calibrated, it's good to a
few tens of millivolts, depending on temperature. The diode question is the
one that could sink it, and Step 1 answers it.

What you'd be buying: an ADS1115 breakout, an MCP6002, three resistors, two
capacitors, a scrap of perfboard, and a permanent bodge onto an 0805 pad.
What you'd get: voltage only, about as accurate as an INA226 out of the
box, as long as the calibration holds.

### Route B: read the meter's own serial pins

This is the only route that reuses the meter's brain (its ADC and its
factory calibration), and it costs about ten minutes to test.

`V G R T O` has RX and TX labels. If the firmware streams readings on T, the
Pi only needs ground and one receive wire. A UART transmit line sits high
when idle, so a multimeter on T tells you most of the story before any
adapter gets connected: a steady reading equal to V is promising, and 0 V
means nothing's there.

My honest odds are low, maybe one in four. Cheap meters usually keep those
pads for factory programming or for a "communication" version of the
product, and the firmware might only answer if sent a command nobody has
documented. Even if it works, it's voltage only, at whatever resolution
and accuracy the meter has, and it's tied to a product with no datasheet.

### Route C: snoop on the LCD driver

The microcontroller sends segment data to U4 over three wires (chip-select,
write clock, data) if U4 really is an HT1621-type part. The ESP32 could
capture that and turn segment patterns back into digits. It's a fun reverse
engineering project and a bad battery sensor: the result is only as fine as
the display. If it shows 0.1 V steps, each step is a quarter to a sixth
of the pack's usable range. Not recommended.

### Route D: an INA226 on the same two terminals

This is `Hardware_Roadmap.md` §2's plan, done in two stages so it starts
paying off on day one.

**Stage 1, voltage only.** An INA226 breakout (the common CJMCU-226 has a
separate `VBS` pin) wired to the battery exactly like the old meter, plus
four wires to the Pi:

```
Battery +  --[0.5 to 1 A inline fuse, close to the terminal]-- INA226 VBS
                                                     (IN+ and IN- tied to VBS for now)
Battery -  ==== already common with Pi GND (Step 0b checks this)
INA226 VCC -- Pi 3V3 (pin 1)    INA226 GND -- Pi GND (pin 6)
INA226 SDA -- Pi pin 3          INA226 SCL -- Pi pin 5
A0, A1 left at the default -> address 0x40
```

If your breakout has no separate VBS pin, the board ties VBUS to IN−, so
connect IN+ and IN− together to battery +.

Out of the box the bus voltage is good to ±0.1% gain and ±7.5 mV offset,
worst case. That's about ±20 mV at 13 V before any calibration, and drift is
10 to 50 ppm/°C. The LSB is 1.25 mV. In other words, uncalibrated it
already matches or beats a calibrated Route A, with one chip, no op-amp
and no soldering onto the meter.

**Stage 2, current.** Add a 50 A / 75 mV shunt in the battery + lead,
upstream of the SSR-50DD so it sees everything. IN+ goes on the battery
side, IN− on the load side. The shunt is 1.5 mΩ, so the INA226's ±81.92 mV
input covers about ±54 A. With a current LSB of 2 mA the calibration
register is 0.00512 / (0.002 × 0.0015) ≈ 1707. That gives coulomb counting,
charge detection and the pack's internal resistance (ΔV/ΔI on every motor
start), which is everything §3 says voltage alone can't. Stage 2 means
cutting into the main battery lead with proper lugs and wire, so it's real
work and not part of this first step.

The old meter can stay across the battery as a glance display. It and the
INA226 don't interact.

### Side by side

| | A: tap divider | B: meter's UART | C: snoop LCD | D: INA226 |
|---|---|---|---|---|
| Reuses from the meter | analog front end | the whole meter | display data | nothing (it stays as a display) |
| Added parts | ADS1115, op-amp, 3 R, 2 C, perfboard | maybe a level divider | ESP32 pins + firmware | one breakout, one fuse |
| Changes to the meter | solder onto an 0805 pad | none | 3 wires on fine-pitch pins | none |
| Voltage error | tens of mV, after calibration | whatever the meter manages | one display step | ±20 mV worst, uncalibrated |
| Current | no | no | no | yes, at Stage 2 |
| Odds it works | high | low | medium, lots of effort | high |

---

## 5. Recommendation

Do D, Stage 1. It's the same parallel connection the meter already proved,
it puts a real voltage on the Pi in an afternoon, and its first job is to
measure the sag while driving, which turns §3's argument for Stage 2 into a
number. The chip carries straight on into Stage 2 with no rework.

Try B for ten minutes if you're curious, since it costs nothing.

Do A only if you want the exercise. It's a good one: a high-impedance
source, buffering, a differential input, an error budget that gets
multiplied by 41, and two-point calibration. Just don't let the robot
depend on it.

---

## 6. Steps, with predictions

One step at a time, paste the readings, then move on.

**Step 0 (everything off).**

- 0a. Is there a fuse in the meter's battery + lead? If not, put a 0.5 to
  1 A inline fuse as close to the + terminal as possible before anything
  else goes on that lead. It's a 30 Ah pack, and a sense wire shorted to
  the frame will carry far more current than that wire can take.
- 0b. Continuity from the battery − terminal to Pi header pin 6.
  *Prediction: continuity (under 1 Ω), because the Pi's supply runs off
  this pack.* If it's open, the Pi's supply is isolated or the Pi is on
  mains, and the sensor's ground needs one deliberate wire to battery −.
- 0c. (Pi on.) DC volts from header pin 3 (SDA) to pin 6. *Prediction:
  3.3 V.* If it reads 3.6 V or more, the LCD's PCF8574 backpack is pulling
  the bus up to 5 V. The new chips will tolerate that (INA226 and ADS1115
  digital pins are rated above 5 V), but the Pi isn't, and that would be an
  existing problem worth fixing on its own.

**Step 1: meter on the pack as before, motors' SSR off.** Black probe on
battery − for every reading.

| # | Red probe on | Prediction |
|---|---|---|
| 1 | battery + | 13.0 to 13.4 V at rest, depending on charge |
| 2 | meter `G` pad | 0.00 V. If it's 0.6 to 0.8 V, the 1N4007 is in the negative leg |
| 3 | meter `V` pad | 3.3 V above reading 2 (5.0 V would also be plausible) |
| 4 | meter `T` pad | steady, equal to V, if it's an idle UART transmitter; otherwise 0 V |
| 5 | meter `R` pad | equal to V (pulled up) or 0 V |
| 6 | both pads of each `30E` and the `01D` resistor | one pad at about 2.4% of reading 1 (≈0.32 V); the pad between the two `30E`s should be about 6.8 V, but expect it to read nearer 6.1 V because your multimeter's own 10 MΩ input loads a node that's ~1 MΩ inside; the far end equal to reading 1, or 0.6 to 0.7 V below it if the divider sits after the diode |

If reading 6 doesn't show a ~2.4% node anywhere, my resistor codes are
wrong and Route A needs a rethink before anything is soldered.

**Step 2B (only if reading 4 sat steady at V).** USB-to-serial adapter on
the Windows PC, adapter GND to meter G, adapter RX to meter T, charger
unplugged. Open a serial monitor and step through 9600, 115200, 4800,
2400, 19200, 38400, 57600 baud. *Prediction: nothing readable at any of
them.*

**Step 2D: INA226 Stage 1, wired as in §4.** On the Pi:

```bash
i2cdetect -y 1
```

*Prediction: 0x27 (LCD), UU at 0x68 (DS3231, claimed by the kernel's RTC
driver), maybe 0x57 (the EEPROM on the HW-084 RTC board), and a new 0x40.*

```bash
i2cget -y 1 0x40 0xFE w
```

*Prediction: `0x4954`*, which is TI's manufacturer ID 0x5449 with its bytes
swapped. i2cget prints words low byte first and the INA226 sends high byte
first, so every word read below needs the same swap.

```bash
i2cget -y 1 0x40 0x02 w
```

Decode the value it prints (example: `0x7c29`):

```bash
python3 -c "import sys; w=int(sys.argv[1],16); print(round((((w&0xff)<<8)|(w>>8))*1.25e-3,4),'V')" 0x7c29
```

That example prints `13.275 V`. *Prediction: within ±0.02 V of a
multimeter held on the INA226's VBS and GND pins.* Measure there, not at
the battery, so wire drop doesn't count against the chip.

**Step 3, first drive with voltage logged.** Write this down before the
drive: resting voltage stays put within a few mV over a minute, and the
voltage dips by somewhere between 100 and 400 mV on hard accelerations
and comes back within a second or two when the motors stop. Any dip over
100 mV is a dip voltage-only percentage can't tell apart from discharge.

---

## 7. Software shape (not built yet)

Same as `Hardware_Roadmap.md` §2.3: a small node publishing
`sensor_msgs/BatteryState`, read over I²C the way `lcd_display.py` already
talks to its own I²C device, and one more dashboard tile. Two INA226
details to carry into it:

- Set the configuration register to `0x4527` (16 averages, 1.1 ms
  conversions, continuous). Each result then averages about 35 ms, which
  smooths out the MDD20A's PWM ripple.
- Every word read needs the byte swap from Step 2D. SMBus word reads are
  little-endian, and the INA226 isn't.

Until Stage 2 exists, publish voltage only and leave `percentage` as NaN,
which is what the message definition says to do when it's unknown. A
made-up percentage from §3's table would be wrong for most of the pack's
life and would look authoritative on the dashboard.

---

## 8. What would change this plan

- Reading 4 steady at V and readable text in Step 2B. Then B becomes a free
  way to get the meter's number, though it's still voltage only.
- The divider turning out to sit before the diode, and someone wanting the
  Route A exercise. Fine, as long as D still goes in for the robot itself.
- No INA226 in stock. Route A's parts (ADS1115 + MCP6002), with a fresh
  divider of your own instead of the meter's, is the fallback, using the
  same buffer and calibration recipe from §4.
