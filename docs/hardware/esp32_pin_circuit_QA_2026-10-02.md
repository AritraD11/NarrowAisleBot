# ESP32 pin circuit, QA 2 Oct 2026

File under test: `esp32_pin_circuit.svg` and `.png`, built by `esp32_pin_circuit.py` from `aislebot_esp32.ino` v3.0.

## What was checked

| Check | How | Result |
|---|---|---|
| Pins on the drawing equal the firmware | Labels read back out of the SVG and compared with the `#define` block, separately from the generator's own parser | left side 36, 39, 34, 35, 32, 33, 25, 26 and right side 4, 16, 17, 18, 19, 21, 22, 23 both match |
| Sensible pin choice | 16 distinct pins, none in {0, 2, 5, 12, 15} (strapping), 6 to 11 (flash), 1 and 3 (UART0 to USB) | pass |
| Input-only pins flagged | 34, 35, 36, 39 carry the asterisk and the note | pass |
| Direction signs | `MOTOR_DIR_SIGN` equals `ENC_DIR_SIGN`, drawn as {-1, +1, -1, +1} | pass, generator stops if they differ |
| Shifter channels and wire colours | H0 to H7 and L0 to L7 against `Bench_Test_Map.md`, GPIO against the firmware | pass, generator stops if they disagree |
| Drift | Regenerated from the current repo | byte-identical to the committed file |
| Newer commits on `main` | Fetched, diffed | main gained the 1 Oct handoff Part 2 and `tools/bag_cmd_chain.py`. Neither touches the firmware, the wiring docs or any pin, so the drawing is still current. Merged into the branch. |
| Text layout | Chromium check for text overlapping text or leaving the canvas, on the real fonts | clean |
| Visual | Full image and zoomed crops of the encoder side and the driver side | wires land on the labelled pins, power and ground flags present, no stray lines |

## Facts taken from the docs, not the code

PWM1/DIR1/PWM2/DIR2 and M1A/M1B/M2A/M2B pin names, driver logic GND to ESP32 GND, VB+ and VB- on 24 V, the 5 V and 24 V sources, "Red to MxA, Black to MxB" (`Master_Reference.md` 2.5, 3.1, 3.2, 4.2). USB powers the ESP32 today because the VIN-from-buck fix is listed as "never actually done" in `Hardware_Roadmap.md`.

## Not checked

The physical robot. Nothing here was continuity-tested or probed.

## Two repo docs disagree, the drawing follows the newer one

`Master_Reference.md` section 4.3 says encoder wiring is identical on all four motors, Yellow to A and Green to B. `Bench_Test_Map.md` and `LevelShifter_Wiring.md` section 5 say the front GTK08 pair is Green = A and White = B, with Yellow as the unused Z index. The drawing uses the second, because it is the later document and the first one carries a warning pointing at it. Both bench docs also say to confirm against the physical wire, which the drawing repeats.
