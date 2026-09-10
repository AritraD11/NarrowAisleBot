# Geometry extracted from the DXF exports

Read directly out of the DXF files in Google Drive on 9 Sep 2026. These are not measurements, estimates, or reconstructions. Every number below is a literal coordinate stored in the CAD file by SolidWorks.

Both files declare `$INSUNITS = 4`, so all units are millimetres. Both carry a `SOLIDWORKS Educational Product. For Instructional Use Only.` watermark as MTEXT, which will appear on any export made from this licence.

## Base platform (`AislebotChasisLowerPlate.DXF`)

Outline is four straight lines, a plain rectangle with no fillets and no cut-outs:

| | Value |
|---|---|
| `$EXTMIN` | (−500, −125) |
| `$EXTMAX` | (+500, +125) |
| Overall | **1000 × 250 mm** |

That confirms the 1000 × 250 mm figure in `docs/Master_Reference.md` §2.1 against the CAD itself.

### Wheel-mount hole pattern, and why it settles the l₁ / l₂ question

Twelve Ø5.0–5.1 mm holes sit on two rows at y = ±112 mm. They form six pairs, each pair spaced 54 mm apart:

| Row | Hole x-positions | Pair midpoints |
|---|---|---|
| y = −112 | −360, −306, −27, +27, +376, +430 | **−333**, 0, **+403** |
| y = +112 | −430, −376, −27, +27, +306, +360 | **−403**, 0, **+333** |

The midpoints are l₁ = 403 mm and l₂ = 333 mm, exactly as documented, and they land on opposite sides at opposite ends. That is the asymmetry, visible directly in the drilling: one side carries its wheel at 403 mm forward and 333 mm aft, the other side mirrors it. Offset l₁ − l₂ = 70 mm.

The extra pair at x = 0 on both rows is a third mount position at mid-length, which matches the centre bracket visible in the underside render.

### The 250 mm versus 315.38 mm question is now answered

`docs/Master_Reference.md` §2.2 labels 250 mm as "track (2d)", but the table in §2.1 gives d = 157.69 mm, implying 2d = 315.38 mm. The DXF resolves it: the **plate** is 250 mm wide (edges at y = ±125) and the **mount holes** are at y = ±112, while the wheel centreline sits at d = 157.69 mm. The wheels therefore stand proud of the plate edge by 157.69 − 125 = 32.69 mm per side.

Both numbers are correct and they describe different things. §2.2's diagram mislabels the plate width as the track. That caption needs fixing before it goes in the report.

### Other holes

Four clusters of six Ø5.0 mm holes at x = ±58 and x = ±487, each cluster at y = ±10, ±97, ±117. The x = ±487 clusters sit 13 mm in from the ends; the x = ±58 clusters flank mid-length.

## Top plate (`AisleBotTopPlate.DXF`)

| | Value |
|---|---|
| `$EXTMIN` | (−150, −125) |
| `$EXTMAX` | (+150, +125) |
| Overall | **300 × 250 mm** |
| Corner fillets | R10 (`$FILLETRAD = 10.0`) |

Width matches the base platform exactly. The outline necks in to x = ±110 between y = ±26 and y = ±36, a waist cut-out on both long sides, formed from lines and R10 arcs.

Holes: Ø15.1 mm dead centre at (0, 0). Ø5.6 mm at x = ±117.5 and ±142.5, y = ±31.495 and ±73.495. Ø5.1 mm at x = ±130, y = −52.505 / −0.005 / +52.495. Ø5.6 mm at (±17.678, ±17.678), a 45°-rotated square pattern on a 25 mm radius bolt circle.

## How this was obtained, and how to extend it

DXF is plain text, so the Google Drive connector can hand over the whole file and it can be parsed here. The proprietary formats cannot: `.SLDASM`, `.SLDPRT`, `.SLDDRW` need SolidWorks, and `.DWG` needs a converter this environment does not have.

To pull exact geometry for any other part, export it from SolidWorks as DXF and drop it in Drive. The steel chassis members currently exist only as `.DWG` (`SteelChasisLengthRod.DWG`, `SteelChasisBreadthPlate.DWG`, `SteelChasisBreadthRodMiddle.DWG`, plus their sheet-metal flat patterns). Re-exported as DXF, they would give exact rod lengths, plate sizes, bend allowances, and gauge.

Still unknown, because a flat DXF outline carries no thickness: plate gauge, bracket standoff height, and anything in the third dimension. Those come from the `.SLDDRW` sheets or from measuring the real part.
