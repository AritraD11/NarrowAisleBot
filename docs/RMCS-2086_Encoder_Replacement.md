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

### The encoder (confirmed from Robokits + the repo)

| Property | Value |
|---|---|
| Type | **Optical, incremental quadrature** (2-channel A/B) |
| Resolution | **500 lines → 2000 PPR** at the base-motor shaft (×4 quadrature) |
| Output CPR at the wheel | **≈ 93,132** (2000 × 46.6 effective gear) — the `ENCODER_CPR` in firmware |
| Location | On the **rear of the base DC motor**, before the 47:1 gearbox |
| Encoder supply | **5 V** (this is why the NAB needs the TXS0108E level shifter to the 3.3 V ESP32) |
| Wiring (6 leads total) | 2 thick: **Motor +, Motor −**. 4 thin: **Red = +5 V, Black = GND, Yellow = Channel A, Green = Channel B** |

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

*Sources: [Robokits RMCS-2086 product page](https://robokits.co.in/motors/rhino-planetary-geared-24v-motor/100w-24v-encoder-servo-motor/rhino-servo-24v-60rpm-100w-ig52-extra-heavy-duty-planetary-encoder-servo-motor-160kgcm) · [AS5047P (Amazon.in)](https://www.amazon.in/AS5047P-Peripheral-Interface-Applications-Diametrical/dp/B0FLR68Z6Y) · uploaded RMCS-2077 datasheet · `docs/Master_Reference.md` §2.3/§4.3. Prices July 2026 — verify before ordering.*
