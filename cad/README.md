# CAD

Source of record for the chassis geometry, and a map of where the rest of it lives.

## In this repo

```
cad/
├── chassis/
│   └── AislebotBasePlatform_SteelChasis.SLDASM   ← full base platform assembly
├── wheels/
│   ├── MecanumLeftWithHub.SLDASM                 ← left mecanum wheel + hub, native SW
│   ├── MecanumRightWithHub.SLDASM                ← right mecanum wheel + hub, native SW
│   ├── am-3479La 6 SR Mecanum Left with Standoffs.STEP   ← left wheel, neutral format
│   └── am-3479Ra 6 SR Mecanum Right with Standoffs.STEP  ← right wheel, neutral format
├── motor/
│   └── geared_DC_motor.SLDPRT                    ← Rhino RMCS-2086 model
└── renders/                                      ← real CAD renders, for report figures
```

`.SLDASM` / `.SLDPRT` are native SolidWorks (2019+), a proprietary binary container, not the older OLE2 format. Nothing but SolidWorks or eDrawings opens them. The two `.STEP` files are AP214 text and open in free viewers (eDrawings Viewer, FreeCAD, Autodesk Viewer, OnShape).

## Everything else is in Google Drive

Three shared folders hold the complete design. The Drive connector can list and search them from a Claude session, but this environment's network policy blocks `drive.google.com`, so file *contents* cannot be pulled down directly. Anything needed for the report has to be committed to this repo.

The pieces that matter for report figures:

**Real CAD renders** (folder `AislebotPatentObjects` / `Patent_4_Crazy_bot`)

| File | What it shows |
|---|---|
| `AislebotBasePlatform_SteelChasis_Topview.JPG` | full platform, top |
| `AislebotBasePlatform_SteelChasis_bottomview.JPG` | full platform, underside with the centre bracket |
| `AislebotBasePlatform_SteelChasis_sideview.JPG` | full platform, side |
| `SteelChasis_topview.JPG` / `_bottomview.JPG` / `_sideview.JPG` | bare steel frame, three views |
| `Chassis.png` | chassis render |

**SolidWorks drawings**, the dimensioned 2D sheets, in `Aislebot_Assembly`

| File | Part |
|---|---|
| `SteelChasisAssembly_drawing.SLDDRW` | the steel chassis assembly |
| `AislebotChasisUpperPlate_New.SLDDRW` | upper plate |
| `AislebotChasisLowerPlate.SLDDRW` | lower plate |
| `SteelChasisLengthRod_drawing.SLDDRW` | length rod |
| `SteelChasisBreadthPlate_drawing.SLDDRW` | breadth plate |
| `SteelChasisBreadthRodMiddle_drawing.SLDDRW` | middle breadth rod |

These are the real dimension source. Exported to PDF from SolidWorks they become usable directly as report figures, and they settle every dimension question below without anyone measuring pixels.

**DWG exports** in `aislebot_assembly_backup_sw_urdf_both`, including `Flat pattern - SteelChasisLengthRodSheetMetal.DWG` and the matching breadth-plate and breadth-rod flat patterns. Flat patterns carry exact sheet metal dimensions and bend allowances.

Checked and ruled out: `Monika_aislebot1.pdf`, `Monika_compiled_4.pdf`, `Monika_aislebot_chair_3.pdf`, `Monika_aislebot_trolley_2.pdf`. These are patent figure sheets (their only text is reference numerals like "FIG. 1f", "100", "200"), not dimensioned drawings.

## Dimensions currently treated as ground truth

From `docs/Master_Reference.md` §2.1/2.4, sourced there from the SolidWorks model:

| Parameter | Symbol | Value |
|---|---|---|
| Chassis length | | 1000 mm |
| Chassis width | | 250 mm |
| Outer wheel longitudinal distance (FR, RL) | l₁ | 403 mm |
| Inner wheel longitudinal distance (FL, RR) | l₂ | 333 mm |
| Half track width | d | 157.69 mm |
| Asymmetry offset | l₁ − l₂ | 70 mm |
| Wheel radius | a | 76.2 mm (152.4 mm OD, 6") |

Two things still open, both answerable from the `.SLDDRW` sheets above:

1. §2.2's top-view sketch labels 250 mm as "track (2d)", but 2 × 157.69 = 315.38 mm. Those can legitimately be different quantities (frame width against wheel-to-wheel track, if the wheels sit proud of the frame edge), but the document currently uses one number for both, which reads as a mislabel.
2. Plate thickness, steel gauge, bracket standoff height, and the bracket hole pattern are not recorded anywhere in the repo.

## Note on the removed OpenSCAD model

An earlier commit on this branch added a parametric OpenSCAD reconstruction of the chassis plus rendered views. It was removed on request: the report uses real CAD imagery, not generated geometry. It remains in git history if it is ever wanted for something else.
