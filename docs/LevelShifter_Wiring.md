# TXS0108E Level Shifter — Complete Wiring Reference (RETIRED, 4 Aug 2026)

> **This hardware is no longer on the robot.** The dual-TXS0108E design
> documented below was replaced on 4 Aug 2026 with a single **8-channel
> discrete MOSFET (BSS138-style) bidirectional level shifter board** — no IC,
> no OE pin, per-channel LEDs, all four encoders on one board. Current wiring:
> `Bench_Test_Map.md` §"Full 8-channel wiring — all four encoders on one
> board". This document is kept because the underlying principles (signal
> direction, common ground, the GTK08-vs-RMCS wire-colour trap in §5) still
> apply — only the shifter part itself changed. See `Master_Reference.md`
> §2.5 for the hardware-change note.

Two 8-channel TXS0108E boards translate the 5 V encoder signals down to the
ESP32's 3.3 V GPIOs. **U1 handles the front pair (FR, FL), U2 handles the rear
pair (RR, RL).** Each board uses 4 of its 8 channels.

This document exists because the bench calibration run on 3 Aug 2026 returned
`DEAD_NO_COUNTS` on all four motors while the wheels were physically spinning.
That symptom points at this interface, which has already failed twice before
(`Research_Journal.md` §7.12).

---

## 1. The signal direction (get this right first)

```
   ENCODER (5 V)              TXS0108E                ESP32 (3.3 V)
   ─────────────              ────────                ─────────────
   A / B outputs  ────────►   B side    ══════►   A side  ────────►  GPIO
                              (VCCB=5V)          (VCCA=3.3V)
```

**Encoder goes to the B side. ESP32 goes to the A side.** A is always the
low-voltage side on a TXS0108E. Swapping them is a silent failure: no smoke,
just no usable signal.

---

## 2. Power rails — wire these point-to-point, not daisy-chained

| Pin | Connect to | Notes |
|---|---|---|
| **VCCA** | ESP32 `3V3` pin | 3.3 V low-voltage side |
| **VCCB** | Buck converter 5 V output | 5 V high-voltage side. **Not** the ESP32's 5V/VIN |
| **GND** | Common ground bus | Must be shared by ESP32 **and** buck **and** encoder |
| **OE** | Tie to VCCA (3.3 V) | Output Enable. **Floating or LOW = all 8 channels Hi-Z** |

> **This is the part that has bitten this project twice.** The original build
> daisy-chained U2's VCCA and VCCB *from U1* (`Research_Journal.md` §4.4). Both
> May 2026 encoder failures traced to broken solder joints on that chain.
>
> A single break in the shared 5 V feed kills **every channel on both boards at
> once** — which is exactly the all-four-dead pattern the calibration run
> produced. Run separate wires from the buck to each board's VCCB, and from the
> ESP32 3V3 to each board's VCCA.

**Power-up order:** GND first, then VCCA (3.3 V), then VCCB (5 V). The
TXS0108E expects its low side up before its high side.

---

## 3. U1 — FRONT pair (FR, FL) — now GTK08 encoders

| TXS0108E U1 | ESP32 pin | GPIO | Signal | PCNT unit |
|---|---|---|---|---|
| A1 | SP | **36** | FR Encoder A | PCNT_UNIT_0 |
| A2 | SN | **39** | FR Encoder B | PCNT_UNIT_0 |
| A3 | G34 | **34** | FL Encoder A | PCNT_UNIT_1 |
| A4 | G35 | **35** | FL Encoder B | PCNT_UNIT_1 |
| B1 | — | — | FR encoder A output (5 V) | |
| B2 | — | — | FR encoder B output (5 V) | |
| B3 | — | — | FL encoder A output (5 V) | |
| B4 | — | — | FL encoder B output (5 V) | |
| A5–A8, B5–B8 | unused | | leave open | |

## 4. U2 — REAR pair (RR, RL) — RMCS-2086 optical encoders

| TXS0108E U2 | ESP32 pin | GPIO | Signal | PCNT unit |
|---|---|---|---|---|
| A1 | G32 | **32** | RR Encoder A | PCNT_UNIT_2 |
| A2 | G33 | **33** | RR Encoder B | PCNT_UNIT_2 |
| A3 | G25 | **25** | RL Encoder A | PCNT_UNIT_3 |
| A4 | G26 | **26** | RL Encoder B | PCNT_UNIT_3 |
| B1 | — | — | RR encoder A output (5 V) | |
| B2 | — | — | RR encoder B output (5 V) | |
| B3 | — | — | RL encoder A output (5 V) | |
| B4 | — | — | RL encoder B output (5 V) | |
| A5–A8, B5–B8 | unused | | leave open | |

---

## 5. Encoder wire colours — THE TWO TYPES DIFFER

The front motors now carry GTK08 encoders while the rears keep the original
RMCS optical units. **The colour codes are not the same, and `Green` means
different things on each.** Wiring a GTK08 by the old RMCS convention is an
easy and completely silent mistake.

| Wire | RMCS-2086 (rear, optical) | GTK08 (front, 1000 PPR) |
|---|---|---|
| Red | +5 V | +5 V |
| Black | GND | GND |
| **Green** | **Channel B** | **Channel A** |
| **Yellow** | **Channel A** | **Z / index** |
| White | — | **Channel B** |

> **Verify against your actual GTK08 label or datasheet before trusting this
> table** — colour codes on these industrial encoders vary between suppliers.
> The GTK08 layout above is the standard for this encoder family (the same one
> where you confirmed Yellow = Z during Mega testing).
>
> The failure mode to watch for: if Yellow (Z index) is wired into the A input,
> you get one pulse per motor revolution instead of 1000 — near-zero counts
> that look like a dead encoder but are actually a colour mix-up.

**Encoder power:** Red goes to the **buck 5 V rail, not the ESP32.** Black goes
to the common ground bus.

---

## 6. Bench verification (10 minutes, before flashing anything)

Do these with a multimeter, system powered, motors off:

1. **VCCA on both boards reads 3.3 V** (probe to common GND).
2. **VCCB on both boards reads 5.0 V.** If one board reads 0 V, you have found
   the broken daisy-chain link.
3. **OE on both boards reads 3.3 V.** If it reads 0 V or floats, every channel
   is Hi-Z and the ESP32 sees nothing — this alone produces the exact
   all-four-dead log.
4. **Continuity: encoder GND ↔ ESP32 GND ↔ buck GND.** All three must be one
   node. A missing common ground makes level shifting meaningless.
5. **Encoder Red reads 5 V at the encoder connector itself**, not just at the
   buck output.
6. Turn a wheel by hand and probe that encoder's A output **on the B side of
   the shifter**: it should swing 0 V ↔ 5 V. Then probe the matching **A-side**
   pin: it should swing 0 V ↔ 3.3 V. This tells you which side of the shifter
   the signal dies on.

Then flash `firmware/nab_encoder_isolation_test_esp32.ino` and turn each wheel
by hand — it prints live A/B pin levels and raw PCNT counts with the motors
completely off.

---

## 7. If the TXS0108E keeps causing trouble — the divider fallback

These encoder signals are **unidirectional** (5 V encoder → 3.3 V ESP32, never
the reverse). The TXS0108E is a *bidirectional* auto-direction-sensing part,
which is far more complexity than this job needs, and it is the single
component with the worst reliability record in this build.

A two-resistor divider per channel is a robust alternative with no OE pin, no
direction sensing, and no power-sequencing requirement:

```
  Encoder A (5 V) ──[ 1.0 kΩ ]──┬── ESP32 GPIO (3.3 V)
                                │
                             [ 2.0 kΩ ]
                                │
                               GND
```

5 V × 2.0/(1.0+2.0) = **3.33 V** — right at the ESP32 rail. Eight channels
needs sixteen resistors, which is tedious but effectively unbreakable. With
short leads the RC rolloff is far above the GTK08's ~188 kHz worst-case output
rate, so it costs nothing in bandwidth.

The AS5047P retrofit path (`RMCS-2086_Encoder_Replacement.md` §8) removes this
interface entirely by running the encoders natively at 3.3 V.

---

## 8. Input-only pins — a constraint worth knowing

GPIO **34, 35, 36, 39** are input-only on the ESP32 and have **no internal
pull-ups or pull-downs**. That is fine for encoder inputs, but it means when the
shifter's outputs go Hi-Z (OE low, or VCCB missing) these pins float rather than
settling to a defined level. Floating inputs can read as stuck-high, stuck-low,
or noise — do not interpret a steady reading on these pins as proof that a
signal is present.

---

*Sources: `Master_Reference.md` §4.3–4.4 · `Research_Journal.md` §3.6, §4.4,
§7.12 · TXS0108E datasheet (TI SCES650) · bench calibration log, 3 Aug 2026.*
