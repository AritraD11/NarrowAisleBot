# Breadboard Bench Test — The Map

ESP32 on a breadboard. Two encoders. No motor drivers. Goal: find out, once and
for all, whether the TXS0108E level shifters are the problem.

---

## The one thing to understand first

**You cannot wire a 5 V encoder straight into an ESP32 pin.** The ESP32 is not
5 V tolerant (3.3 V max, absolute max ~3.6 V). The GTK08 outputs ~4.7 V
push-pull. That is why the level shifter exists at all.

This is the difference from the Mega tests — on the Mega you could just plug the
encoder in directly and get a clean baseline. On the ESP32 you cannot. So we
build the baseline a different way: with a **resistor divider**, which is dumb,
cheap, and has nothing in it that can fail.

That gives us three stages, in this exact order:

| Stage | What's in the signal path | What it proves |
|---|---|---|
| **A** | Resistor divider | ESP32 pins + encoders + wiring are good |
| **B** | Level shifter #1 | Whether shifter #1 works |
| **C** | Level shifter #2 | Whether shifter #2 works |

**Do not skip Stage A.** If you go straight to the shifter and it fails, you
still won't know whether the shifter or the ESP32 pin is at fault — which is
exactly the ambiguity that has cost this whole session.

---

## Common to every stage — ground

One ground rail on the breadboard. Everything lands on it:

```
   ESP32 GND ──┐
   Buck  GND ──┼──── breadboard GND rail
  Encoder GND ─┤
  Shifter GND ─┘     (Stage B/C only)
```

Wire it deliberately. Do not rely on whatever hidden path has been quietly
doing the job in the Mega tests.

---

## STAGE A — Divider baseline (no shifter)

Build this for **each of the 4 signal lines** (Enc1-A, Enc1-B, Enc2-A, Enc2-B):

```
  ENCODER OUT (5 V)
        │
      [ 1 kΩ ]
        │
        ├──────────────►  ESP32 GPIO   (this junction = 3.33 V logic)
        │
      [ 2 kΩ ]
        │
       GND
```

5 V × 2/(1+2) = **3.33 V**. Right at the ESP32 rail. Eight resistors total for
four channels.

**No pull-up resistors in this stage.** A pull-up to 3.3 V would change the
divider ratio. Pull-ups are for Stage B/C only.

Pin landing:

| Signal | ESP32 pin |
|---|---|
| Enc1-A | GPIO 36 |
| Enc1-B | GPIO 39 |
| Enc2-A | GPIO 34 |
| Enc2-B | GPIO 35 |

### The control trick (worth the extra 2 jumpers)

GPIO 36 and 39 are input-only, have no internal pull resistors, and carry a
documented Espressif glitch erratum. So also tap **Enc1-A and Enc1-B to GPIO 13
and GPIO 14** at the same time — same divider junction, just a second jumper to
a second pin.

```
      divider junction ──┬──► GPIO 36   (suspect pin)
                         └──► GPIO 13   (clean control pin)
```

GPIO 13/14/27 are full-featured, no erratum, unused in the final build. If 13
counts clean and 36 doesn't, the **pin** is the problem, not the shifter. One
wheel turn separates three hypotheses.

---

## Which shifter board are you using?

Two different parts are in play in this project, and they wire up differently.

| | **TXS0108E** (IC type) | **Discrete MOSFET** (BSS138-style) |
|---|---|---|
| Identify by | Single 20-pin IC on board | ~16 transistors, ~32 resistors, no IC |
| Power pins | VCCA / VCCB / GND | LV+ / LV− / HV+ / HV− |
| **OE pin** | **Yes — must be tied to VCCA** | **None — nothing to get wrong** |
| Channels | 8 | 8 |
| Per-channel LEDs | No | Often yes — free visual diagnostic |
| Built-in pull-ups | Yes (weak, with one-shot drive) | Yes (plain resistors) |
| Rising edge | Actively driven | RC-limited by pull-up (slower) |

**Speed check for this project:** worst case is the motor shaft at ~2820 RPM
≈ 47 rev/s, and the GTK08 is 1000 PPR, so each line toggles at about **47 kHz**
(10.6 µs half-period). Both board types have roughly an order of magnitude of
margin on that. Speed is not the limiting factor either way.

**If you have the discrete MOSFET board, prefer it.** No OE pin removes one of
the main suspected failure modes, the per-channel LEDs let you see activity
before opening a serial monitor, and 8 channels covers all four encoders on a
single board.

### Discrete MOSFET board wiring

| Board pin | Connect to |
|---|---|
| **LV+** | ESP32 3.3 V |
| **LV−** | GND rail |
| **HV+** | Buck 5 V |
| **HV−** | GND rail |
| **NC** (if present, middle of HV header) | nothing — spacer |
| H0–H7 | encoder A/B signals (5 V side) |
| L0–L7 | ESP32 GPIO (3.3 V side) |

**LV+ must be the LOWER voltage.** The FET gates reference LV+, so 3.3 V on LV
and 5 V on HV. Swapping them breaks the shifting action.

**Do not add external pull-ups to this board** — it already has them on every
channel, both sides. And note this changes the float test: a dead channel sits
**HIGH** (pulled up), not floating, so a stuck-high line becomes ambiguous
between "working, idle" and "broken." Use the LEDs as the tiebreaker — no
flicker while turning a wheel means that channel is not passing signal.

---

## Full 8-channel wiring — all four encoders on one board

With the 8-channel discrete MOSFET board there is no need to test two
separate shifters turn by turn — one board covers all four encoders at once.
This is the actual, final connection list.

**Channel assignment** (H*x* pairs with L*x* — same number, same physical FET):

| Motor | Wire | Signal | `Hx` (5 V side) | `Lx` (3.3 V side) | ESP32 GPIO |
|---|---|---|---|---|---|
| FR | Green | A | **H0** | **L0** | 36 |
| FR | White | B | **H1** | **L1** | 39 |
| FL | Green | A | **H2** | **L2** | 34 |
| FL | White | B | **H3** | **L3** | 35 |
| RR | Yellow | A | **H4** | **L4** | 32 |
| RR | Green | B | **H5** | **L5** | 33 |
| RL | Yellow | A | **H6** | **L6** | 25 |
| RL | Green | B | **H7** | **L7** | 26 |

This ordering matches the PCNT unit order already used in the production
firmware (FR=unit0, FL=unit1, RR=unit2, RL=unit3), so it's consistent with
the rest of the codebase, not an arbitrary new scheme.

**The wire colours are NOT the same between encoder types** — this exact
mix-up already corrupted a channel once earlier in this project:

| Wire | GTK08 (front, FR/FL) | RMCS-2086 (rear, RR/RL) |
|---|---|---|
| Green | Channel A | Channel B |
| White | Channel B | — |
| Yellow | Z-index (unused here) | Channel A |

Verify against the physical wire, not memory, before landing it on a channel.

**Power:**

| Pin | Connect to |
|---|---|
| Shifter `LV+` | ESP32 `3.3V` |
| Shifter `LV−` | GND rail |
| Shifter `HV+` | Buck `5V` |
| Shifter `HV−` | GND rail |
| All 4 encoders — Red | Buck `5V` (same rail as HV+) |
| All 4 encoders — Black | GND rail (same rail as LV−/HV−) |

One ground rail: ESP32 GND, buck GND, shifter LV−, shifter HV−, all four
encoder Black wires — all on it. No external pull-ups (the board has its
own), `L0`–`L7` jumper straight into the ESP32 GPIOs above, no components in
between.

---

## STAGE B / C — Level shifter in the path (TXS0108E only)

Swap the dividers out, put the shifter in. One shifter at a time.

*(The diagram below is for the TXS0108E. If you're on the discrete MOSFET
board, use the wiring table above instead — same idea, but no OE pin and no
external pull-ups.)*

```
                        ┌──────────── TXS0108E ────────────┐
                        │                                  │
   Buck 5 V ────────────┤ VCCB                        VCCA ├──────── ESP32 3V3
                        │                                  │
                        │                             OE   ├──────── ESP32 3V3
                        │                                  │        (tie to VCCA)
   Enc1-A (5 V) ────────┤ B1                          A1   ├──────── GPIO 36
   Enc1-B (5 V) ────────┤ B2                          A2   ├──────── GPIO 39
   Enc2-A (5 V) ────────┤ B3                          A3   ├──────── GPIO 34
   Enc2-B (5 V) ────────┤ B4                          A4   ├──────── GPIO 35
                        │                                  │
   GND rail ────────────┤ GND                              │
                        └──────────────────────────────────┘

   Channels 5-8 unused — leave open.
```

**Now add the pull-ups.** 10 kΩ from each A-side line to 3.3 V, at the ESP32 end:

```
                 3V3
                  │
               [ 10 kΩ ]
                  │
   A1 ────────────┴──────────► GPIO 36
```

Pull-**up** only, never pull-down — the TXS0108E decides signal direction by
sensing which side gets pulled low, so a pull-down actively fights it.

**Power-up order: GND → VCCA (3.3 V) → VCCB (5 V).**

---

## Decision tree

```mermaid
flowchart TD
    A["STAGE A<br/>divider baseline"] --> A1{Clean counts?}

    A1 -->|NO| B1["Check control pins 13/14"]
    B1 --> B2{"13/14 clean but<br/>36/39 dead?"}
    B2 -->|YES| B3["The PIN is bad.<br/>Remap front encoders<br/>off 36/39."]
    B2 -->|NO| B4["Encoder wiring or<br/>breadboard contact.<br/>Re-seat, fresh rows."]

    A1 -->|YES| C["ESP32 + pins + encoders<br/>CONFIRMED GOOD"]
    C --> D["STAGE B<br/>shifter #1"]
    D --> D1{Clean counts?}

    D1 -->|NO| D2["Shifter #1 is the fault.<br/>Verify OE=3.3V and<br/>VCCB=5V first, then<br/>condemn the board."]
    D1 -->|YES| E["Shifter #1 good"]

    D2 --> F["STAGE C<br/>shifter #2"]
    E --> F
    F --> F1{Clean counts?}
    F1 -->|NO| F2["Shifter #2 is the fault"]
    F1 -->|YES| F3["Both shifters good<br/>→ the original fault was<br/>wiring/contacts, not the<br/>shifters"]
```

---

## Reading the result

You already know what good and bad look like from the Mega runs:

| Pattern | Meaning |
|---|---|
| Bursts of **hundreds** of counts per row, ramping up then tapering, both directions | **Real rotation. Pass.** |
| Alternating `+1 / −1` forever, bouncing between two values, net zero | **Floating/undriven line. Fail.** |
| Sparse ±1 blips, seconds apart, no accumulation | **No signal reaching the pin. Fail.** |
| Nothing at all | Line dead, or nothing wired to that pin |

---

## Pre-power-on checklist

- [ ] One ground rail; ESP32 + buck + encoder (+ shifter) all on it
- [ ] Buck output measured at **5.0 V** before anything is connected to it
- [ ] Stage A: dividers built, **no** pull-ups
- [ ] Stage B/C: **OE tied to VCCA**, pull-ups fitted, dividers removed
- [ ] Encoder wires short, not run parallel to the 5 V pair
- [ ] Fresh breadboard rows — no holes that have had thick jumpers forced in
- [ ] Nothing connected to the motor driver pins (4, 16, 17, 18, 19, 21, 22, 23)

---

## Pin reference

| Motor | A pin | B pin | Internal pull-up? | Notes |
|---|---|---|---|---|
| FR | 36 | 39 | **No** | Input-only + glitch erratum |
| FL | 34 | 35 | **No** | Input-only |
| RR | 32 | 33 | Yes | Full-featured |
| RL | 25 | 26 | Yes | Full-featured |

**Free for control/remap:** 13, 14, 27 (always), plus all 8 driver pins while no
drivers are connected.

**Never use:** 6–11 (SPI flash). **Avoid:** 0, 2, 5, 12, 15 (strapping).

---

## If both shifters turn out fine

Then the fault was always wiring/contacts, and the fix is re-terminating, not
replacing parts. If instead a shifter is confirmed bad, the cheapest robust
replacement is the divider you just used in Stage A — these signals are
unidirectional, so the bidirectional auto-sensing TXS0108E is more complexity
than the job needs. Sixteen resistors for all eight channels, nothing to fail.

*See also: `LevelShifter_Wiring.md` for the full in-robot wiring, and
`firmware/nab_encoder_handturn_diagnostic_esp32.ino` for the float/drive test.*
