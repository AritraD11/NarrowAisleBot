# RMCS-2086 Encoder — Failure & Replacement Options

**The current NAB blocker: the integrated encoders on the two front (RMCS-2086) motors are dead.** This note identifies exactly what encoder they are and lays out every replacement path available in the Indian market, cheapest-and-least-invasive first.

---

## 1. What motor & encoder you actually have

Two Rhino model numbers get confused here — they are the **same base motor + gearbox**, differing only by the encoder:

| Model | What it is | Encoder? |
|---|---|---|
| **RMCS-2077** | *(the datasheet you uploaded)* Planetary Geared DC Motor 160 Kgcm 60 RPM 100 W, 24 V, 1:47, Ø52 body, 12 mm shaft. **Electrical connections: only +VCC (RED) / GND (BLK).** | ❌ **no encoder** (base motor) |
| **RMCS-2086** | *(what the NAB actually uses — see `Master_Reference.md`)* The **same** motor + gearbox **with the rear-shaft optical encoder**. ₹6,200 at Robokits. | ✅ 500-line optical quad |

So the sheet you sent is the *non-encoder* variant — it confirms the motor/gearbox but has a blank encoder table. Your real part is the **RMCS-2086**.

### The encoder (confirmed from Robokits, the repo, AND the physical unit)

A photo of the opened encoder confirms the type and — usefully — its own part number.

| Property | Value |
|---|---|
| Type | **Transmissive optical, incremental quadrature** — a clear **codewheel** (fine radial lines) on the shaft read by a **slotted photo-interrupter** (IR LED + detector). 2-channel A/B. |
| **Encoder PCB marking** | **`RMCS-PLNTY-108U`** · silkscreen `rhinomc.com` · `HDU3.8` · dated `30/6/2K20` · RHINO logo *(verify the exact suffix on your board — the codewheel overlaps it)* |
| Resolution | **500 lines → 2000 PPR** at the base-motor shaft (×4 quadrature) |
| Output CPR at the wheel | **≈ 93,132** (2000 × 46.6 effective gear) — the `ENCODER_CPR` in firmware |
| Location | On the **rear of the base DC motor**, before the 47:1 gearbox |
| Encoder supply | **5 V** (this is why the NAB needs the TXS0108E level shifter to the 3.3 V ESP32) |
| Wiring (6 leads total) | 2 thick: **Motor +, Motor −**. 4 thin: **Red = +5 V, Black = GND, Yellow = Channel A, Green = Channel B** |

> **Why it's the likely failure:** transmissive optical encoders are the delicate kind — a dead IR LED/detector, dust or oil in the optical slot, a bent codewheel, or a cracked flex trace will kill A/B with the disc and board still *looking* perfect. This is exactly the failure a **magnetic** encoder (§8) is immune to — which is why the AS5047P retrofit is the robust long-term fix, not just the cheap one.

---

## 2. First, diagnose before you spend (free)

"Encoder damaged" is very often a **broken wire / cold joint at the connector**, not a dead sensor. Rule this out first — it's the cheapest fix by far:

1. **Continuity-test the 4 encoder leads** (Red/Black/Yellow/Green) from the connector back to the encoder PCB. A single broken A or B line looks exactly like "encoder dead."
2. **Power the encoder (5 V)** and, turning the shaft slowly by hand, scope or logic-analyse **A and B**. Compare a dead front motor against a working rear one. No pulses on one channel → that channel's sensor/track is gone; no pulses on either → power/ground or the whole module.
3. **Reseat the encoder cap/disc** if it's the snap-on type — a dislodged disc or shifted cap kills output.
4. In the NAB's history, the encoder interface already bit you twice at the **TXS0108E** (see `Research_Journal.md`) — verify the level-shifter channel and its 5 V/3.3 V rails before condemning the motor.

If it's a wire or the shifter → **₹0**. Only if the optical module itself is dead do you move to §3.

---

## 3. Replacement options (ranked)

### Option A — Buy replacement RMCS-2086 motors *(surest, plug-and-play)*
- **2× RMCS-2086** from [Robokits](https://robokits.co.in/motors/rhino-planetary-geared-24v-motor/100w-24v-encoder-servo-motor/rhino-servo-24v-60rpm-100w-ig52-extra-heavy-duty-planetary-encoder-servo-motor-160kgcm) / [rhinomc.com](https://rhinomc.com) — **₹6,200 each ≈ ₹12,400**.
- Exact match: `ENCODER_CPR = 93132` unchanged, wiring unchanged, firmware unchanged.
- **Before buying, email Robokits/Rhino support** and ask if they'll sell **just the encoder assembly** for the RMCS-2086 (they do OEM/repair parts). If yes, that's far cheaper than a whole motor and is the real "Option A-lite."
- Downside: you scrap two perfectly good gearmotors over dead encoders.

### Option B — Retrofit an **AS5047P magnetic encoder** *(cheapest, an upgrade, some mechanical work)* ★ recommended
The AS5047P is a 14-bit on-axis magnetic encoder that outputs **A/B/I quadrature (ABI)** — i.e. it speaks the *same language* your ESP32 PCNT already reads. Widely stocked in India ([Amazon.in](https://www.amazon.in/AS5047P-Peripheral-Interface-Applications-Diametrical/dp/B0FLR68Z6Y), ~₹700–1,500 each, diametric magnet included).

- **How:** remove the dead optical encoder, epoxy the diametric magnet centred on the exposed **rear shaft stub**, mount the AS5047P board ~0.5–1 mm above it, wire **A/B → the existing ESP32 encoder pins**.
- **Bonus — no level shifter:** the AS5047P runs at **3.3 V**, so its A/B are already 3.3 V → you can **delete the TXS0108E** for these channels (one less fragile interface — the very interface that's failed before).
- **Resolution:** its ABI resolution is settable via SPI (`ABIRES`). Set it to **512 PPR → 2048 CPR** at the motor shaft; ×47 ≈ **96,256 CPR** at the wheel — essentially the original 93,132, so `ENCODER_CPR` barely changes. (Configuring ABIRES needs a one-time SPI register write; or use a default and just set `ENCODER_CPR` to match.)
- **Caveats:** requires the base motor's **rear shaft to be exposed** (it is, once the optical encoder is off — verify on disassembly) and a small printed/machined mount holding the sensor concentric to the magnet. Fiddly but well-documented and very robust once done.

> **Strong version of Option B: retrofit *all four* motors with AS5047P** (~₹4,000–6,000 total — still cheaper than two new motors). You get four **identical, 3.3 V, magnetic** encoders, kill the optical-encoder fragility that keeps stopping this project, and drop the level shifter entirely. This is the fix I'd pick.

### Option C — External encoder on the **output shaft** *(no motor disassembly)*
Mount a rotary encoder on the 12 mm output shaft / wheel hub (magnetic AS5600, or a 600 P/R optical rotary encoder on a coupling).
- No opening the motor.
- But: reads the **post-gearbox** shaft, so no ×47 multiplication → far fewer counts/rev (e.g. 600–2400 CPR). Usable for velocity/odometry (the same regime as the mini prototype's 537 CPR), just coarser than the original.
- Mechanically awkward on a driven wheel — the output shaft is coupled to the wheel. Usually only worth it if the rear shaft is inaccessible.

---

## 4. Firmware impact

| Path | `ENCODER_CPR` | Level shifter | Wiring | Other |
|---|---|---|---|---|
| A — new RMCS-2086 | 93132 (unchanged) | keep TXS0108E | unchanged | none |
| B — AS5047P (per motor) | set to your ABIRES (≈96256 to match) | **remove** for retrofitted channels | A/B direct to ESP32 (3.3 V) | make `ENCODER_CPR` per-motor if front≠rear |
| C — output-shaft encoder | new, much lower (e.g. 600–2400) | depends on encoder V | new harness | expect coarser velocity |

**Mixing** (Option B on the 2 dead fronts, original optical on the 2 rears) means **two different CPRs on one robot** — change `const float ENCODER_CPR` to a **`float ENCODER_CPR[NUM_MOTORS]`** array in `aislebot_esp32.ino` and index it in the velocity calc. Retrofitting all four (the strong Option B) avoids this and keeps one clean constant.

---

## 5. Recommendation

1. **Diagnose first** (§2) — if it's a wire or the TXS0108E, you're done for ₹0.
2. If the optical module is truly dead: **email Robokits for a spare encoder** (cheap if they'll sell it), and in parallel evaluate **Option B (AS5047P) on all four** — it's cheaper than two new motors, removes the level shifter, and permanently retires the optical-encoder failure mode.
3. Only fall back to **buying two RMCS-2086** (Option A, ₹12,400) if you want zero integration work and the budget is fine.

---

## 6. Why the base motor's rear shaft is exposed (and why that helps)

The RMCS-2077 (base) and RMCS-2086 (encoder) are the **same motor**. On the base version the **rear shaft is left deliberately exposed — that stub *is* the encoder-mounting provision.** Robokits builds the RMCS-2086 by fitting a slotted disc onto that exact shaft and a photo-interrupter board around it. This means:

1. The encoder is a **separate sub-assembly**, not moulded into the motor — so it *can* be sold and fitted on its own.
2. Anyone with the base motors you already own can, in principle, be upgraded to encoder motors by fitting that same assembly.

That's the basis of the request below: if they expose the shaft and sell the disc+sensor as part of the -2086, they should be able to sell you the assembly to (a) repair your two dead fronts and (b) add encoders to the bare base motors you already have.

## 7. Vendor email template (Robokits / Rhino Motion Controls)

> **Send from your IIT Bombay institute email** (an `@iitb.ac.in`-type address), not a personal one. Vendors like Robokits take institutional buyers seriously — it improves the odds they'll sell a spare part they don't normally list, and it lets them raise a **GST invoice** in the institute's name for reimbursement/procurement. Put your **name, roll no., department, and supervisor (Prof. Ambarish Kunwar, BSBE)** in the signature. Send to **support@robokits.co.in** and the rhinomc.com contact form, **attach the photo** of the `RMCS-PLNTY-108U` board with the shaft exposed, and CC your personal address to keep a copy.

```
Subject: Spare encoder for Rhino RMCS-2086 / RMCS-2077 motors (encoder only, not full motor)

Dear Robokits team,

I work on a research robot at IIT Bombay (Department of Biosciences and
Bioengineering) and I use your Rhino 24V 60RPM 160Kgcm IG52 planetary geared
motors. Right now I have four RMCS-2086 units (the version with the 500-line
optical encoder) and four RMCS-2077 base motors with no encoders that are
lying idle because I have nothing to fit on them.

On two of the RMCS-2086 motors the encoder has stopped working (no A or B
output), even though the motor and gearbox are completely fine. I would
rather not buy whole new motors just to replace a dead encoder.

When I opened one up, the encoder is clearly a separate board that sits on
the exposed rear shaft. The PCB is marked RMCS-PLNTY-108U (rhinomc.com,
HDU3.8). It is a transmissive optical type, a codewheel on the shaft with a
slotted sensor over it. Since the RMCS-2086 is just the RMCS-2077 base motor
with this board added, I am hoping you can sell the encoder on its own.

A few questions:

1. Do you sell this encoder board (RMCS-PLNTY-108U with the codewheel and
   mount) as a separate spare part? If yes, the price per piece.
2. Can I fit it myself onto the exposed rear shaft, or does it have to be
   done at your end?
3. Could you confirm the encoder details so I can wire it up: resolution
   (I think 500 lines, 2000 PPR at the motor shaft, around 93,132 CPR after
   the 1:47 gearbox), supply voltage (3.3V or 5V), output type (A/B
   quadrature, is there an index?), the wire colour for each function, and
   the rear shaft diameter.
4. I would like six pieces in total, two to repair the dead motors and four
   for the idle base motors. Please share the per-piece and total price, and
   a GST invoice in the institute's name if possible.

Shipping address is IIT Bombay, Powai, Mumbai 400076.

If the encoder is not available separately, please let me know the cheapest
way to get encoder feedback back on these motors.

Thank you, I look forward to your reply.

Regards,
Aritra Das (Roll No. 25D0074)
Department of Biosciences and Bioengineering, IIT Bombay
Supervisor: Prof. Ambarish Kunwar
[email] · [phone]
```

## 8. AS5047P magnetic retrofit — how it works & whether it will work

**How it works.** The AS5047P is an *on-axis magnetic* rotary sensor:

- You fix a small **diametrically-magnetised magnet** (N–S split *across* the diameter, not top/bottom — the module ships with one) to the **end of the rotating shaft**, centred on the axis.
- The AS5047P chip sits **stationary, ~0.5–2 mm above** the magnet, coaxial with it. As the shaft turns, the magnet's field *direction* turns; the chip's Hall array reads that angle to 14 bits.
- It can emit that angle as SPI, PWM, or — the one you want — **ABI incremental quadrature**: two square waves **A** and **B** 90° apart (plus index **I**), *identical in form to the optical encoder's A/B*. So it drops into the ESP32 PCNT pins with no logic change.

**Why it fits your case well:**
- Your rear shaft is **exposed and rotates** — exactly what it needs. Mount the sensor on the **rear (fast) shaft**, before the gearbox, so you keep the ×47 resolution multiplication (the base motor spins up to 2800 RPM; the AS5047P handles ~28,000 RPM, so no problem).
- It runs at **3.3 V**, so A/B go **straight to the ESP32 — the TXS0108E level shifter is deleted** for these channels (removing the interface that's failed before).
- Set its ABI resolution to **512 PPR (2048 CPR) at the motor shaft** → ×47 ≈ **96,256 CPR at the wheel**, essentially matching the original 93,132, so `ENCODER_CPR` barely changes.

**Step by step (per motor):**
1. Remove the dead optical assembly (disc + photo-interrupter + cap). Note the rear-shaft **diameter and length**.
2. Glue the **diametric magnet** to the flat centre of the rear shaft end (diametric orientation; keep it concentric — this is the critical step).
3. Make/3D-print a **non-ferrous mount** (a cap/bracket) that holds the AS5047P board stationary, **coaxial** with the shaft, ~1 mm above the magnet.
4. Wire **VCC→3.3 V, GND→GND, A→ESP32 enc-A pin, B→ESP32 enc-B pin** (skip the level shifter). Optionally MOSI/MISO/CLK/CSn if you want to set ABIRES over SPI once.
5. In firmware: set `ENCODER_CPR` to (ABI PPR × 4 × 47); calibrate `ENC_DIR_SIGN` as usual so it matches `MOTOR_DIR_SIGN`.

**Will it work? Yes, provided:**
- The magnet is **centred within ~0.5 mm** and the sensor is coaxial and not tilted — off-centre/tilt causes angle error and missed counts. **A printed jig is what makes or breaks this.**
- The rear shaft stub is long/accessible enough to carry a magnet (verify — some stubs are very short).
- Keep loose ferrous material off the sensor face; the close-range magnet field dominates, so the steel shaft itself is fine.

**Don't use an AS5600 here:** it's absolute-only over I2C/analog/PWM with a fixed address — driving four of them for clean A/B quadrature is messy. The **AS5047P's ABI output is the right match** because it *is* quadrature.

---

*Sources: [Robokits RMCS-2086 product page](https://robokits.co.in/motors/rhino-planetary-geared-24v-motor/100w-24v-encoder-servo-motor/rhino-servo-24v-60rpm-100w-ig52-extra-heavy-duty-planetary-encoder-servo-motor-160kgcm) · [AS5047P (Amazon.in)](https://www.amazon.in/AS5047P-Peripheral-Interface-Applications-Diametrical/dp/B0FLR68Z6Y) · uploaded RMCS-2077 datasheet · `docs/Master_Reference.md` §2.3/§4.3. Prices July 2026 — verify before ordering.*
