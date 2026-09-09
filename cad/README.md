# CAD

The actual SolidWorks design of the AisleBot chassis and drivetrain, uploaded 9 Sep 2026. This is the source of record for any dimensioned diagram in the report — not the URDF (which is a simplified box-and-cylinder approximation for simulation, not a dimensioning reference).

## What's here

```
cad/
├── chassis/
│   └── AislebotBasePlatform_SteelChasis.SLDASM   ← full base platform assembly
├── wheels/
│   ├── MecanumLeftWithHub.SLDASM                 ← left mecanum wheel + hub, native SW
│   ├── MecanumRightWithHub.SLDASM                ← right mecanum wheel + hub, native SW
│   ├── am-3479La 6 SR Mecanum Left with Standoffs.STEP   ← left wheel, neutral format
│   └── am-3479Ra 6 SR Mecanum Right with Standoffs.STEP  ← right wheel, neutral format
└── motor/
    └── geared_DC_motor.SLDPRT                    ← Rhino RMCS-2086 model
```

The `am-3479L`/`am-3479Ra` naming matches the AndyMark am-3479 equivalent already noted in `docs/Master_Reference.md` §2.4 for the DekuPro 6" SR mecanum wheels.

## Formats and what can open them

- **`.SLDASM` / `.SLDPRT`** — native SolidWorks. These were saved in a recent SolidWorks version (2019+); they're a proprietary binary container, not the older OLE2 format, so nothing short of SolidWorks or eDrawings can open them. This sandbox has neither, so I organized the files but did not attempt to open them.
- **`.STEP`** (AP214, exported from SolidWorks 2019) — a real, open, text-based exchange format. Free viewers/editors that read it: eDrawings Viewer (free), FreeCAD, Autodesk Viewer (web), OnShape (import). This means the two wheel STEP files are the most portable pieces here if you need to hand geometry to something other than SolidWorks.

I tried parsing the STEP files' raw geometry (vertex point cloud) directly to pull exact wheel dimensions without a CAD kernel. The numbers came out physically implausible (multi-meter bounding boxes for a 6" wheel) — reading a B-rep correctly means resolving placement transforms, which needs an actual CAD kernel (no FreeCAD/pythonocc available here). I did not include those numbers anywhere; treat wheel dimensions as coming from the datasheet values below, not from my attempted extraction.

## The chassis assembly likely has missing references

`AislebotBasePlatform_SteelChasis.SLDASM` is an assembly — it points to child part files (frame plates, standoffs, fasteners) by relative path. Only the two wheel assemblies and the motor were uploaded alongside it, so opening the chassis assembly on a machine other than the one it was authored on will probably show missing-reference errors for suppressed/unlisted children. That's expected and doesn't affect anything above — it's just a heads-up for whoever opens it next in SolidWorks.

## Dimensions already confirmed (use these for diagrams)

`docs/Master_Reference.md` §2.1 states these came from the SolidWorks model already, before this upload:

| Parameter | Symbol | Value |
|---|---|---|
| Chassis length | — | 1000 mm |
| Chassis width | — | 250 mm |
| Outer wheel longitudinal distance (FR, RL) | l₁ | 403 mm |
| Inner wheel longitudinal distance (FL, RR) | l₂ | 333 mm |
| Half track width | d | 157.69 mm |
| Asymmetry offset | l₁ − l₂ | 70 mm |
| Wheel radius | a | 76.2 mm (152.4 mm OD, 6") |

**One thing worth checking against the actual model before it goes in the report:** §2.2's ASCII top-view diagram labels the 250 mm figure as "track (2d)", but 2d from the table above is 2 × 157.69 = 315.38 mm, not 250. Those can legitimately be different things — chassis frame width vs. the wider wheel-to-wheel track if the wheels sit on arms that extend past the frame edge — but the doc currently uses "250 mm" for both, which reads as a mislabel rather than two intentionally different numbers. Worth a five-minute check against the SolidWorks model (or just confirming which one is which) before I draw the top-view diagram, since that's exactly the number a reviewer would double check.

## What I still need from you for exact diagrams

I can't open the native files in this environment, so for anything beyond the table above (steel gauge/plate thickness, hole/standoff spacing, motor mount plate dimensions, fastener pattern) I'd be guessing. Two ways to close that gap:

1. Export dimensioned 2D drawings (SolidWorks `.SLDDRW` → PDF or DXF) for the chassis plate and the wheel hub, and drop them in `cad/` — I can trace exact diagrams straight from those.
2. Or just tell me the specific numbers (plate thickness, hole pitch, standoff height, whatever the report needs) and I'll build the schematic to scale from that plus the table above.
