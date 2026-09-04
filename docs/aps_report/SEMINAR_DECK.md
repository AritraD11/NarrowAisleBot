# APS seminar deck

The slide deck that accompanies `APS_Report_Draft.md`. It exists twice.

| | What it is |
| --- | --- |
| [`NarrowAisleBot_APS_Seminar.pptx`](NarrowAisleBot_APS_Seminar.pptx) | **The one to use.** 16 slides, every figure and the platform photograph already placed, speaker notes on every slide. Open in PowerPoint, Keynote or Slides. |
| Canva design `DAHUKr3fhsk` | The same 16 slides with the image panels left empty, because Canva cannot ingest a file from a private repository. Keep it if you would rather edit in Canva and place the images by hand. |

Both carry identical text and identical numbers.

## The PowerPoint file

Built by [`deck_src/build_deck.js`](deck_src/). Edit the `SLIDES` array there and
rebuild; editing the `.pptx` directly is fine too, but then it is the master and
the generator is stale. `deck_src/preview.py` renders the layout and fails on any
text that would overflow its box.

Fifteen generated figures and one photograph are embedded, 5.9 MB in total.

Canva share links rotate on every access, so the design ID above is the stable
handle. Open the deck from the Canva home page by its title, or ask for a fresh
link. 16 slides, 16:9, white ground, one blue accent.

**No stock imagery.** Canva's generator put one of its own stock robot renders on
the title slide; it has been deleted. Every image that goes into this deck is a
photograph taken of this robot or a figure generated from this project's own
logs. Nothing is pulled from the internet.

## Why the generated text was replaced

Canva's generator produced marketing prose from the outline: "optimizing space
utilization", "enhancing overall agility", "record time". It dropped every
measured number and left its own template's placeholder contact slide
(`hello@reallygreatsite.com`, `123-456-7890`). All sixteen slides were rewritten
element by element against the report, the placeholder slide was replaced with a
closing slide, its stock robot photo was deleted from the title slide, and the
decorative starburst was deleted from every page so the left column is free for
a figure.

## Figures to place

Each content slide has an empty left column, roughly 870 x 680 px at 1920 x 1080.
Drag the PNG in from `docs/aps_report/figures/`. The intended figure is also
written into each slide's speaker notes.

| Slide | Heading | Figure |
| --- | --- | --- |
| 1 | NarrowAisleBot | `docs/robot_photos/2026-08-11_occlusion_trial_cw/cw_000.jpg` — whole platform in three-quarter view, into the empty right panel |
| 2 | The geometry, and why it is asymmetric | `fig01_asymmetric_geometry.png` |
| 3 | What was built | `fig02_system_architecture.png` |
| 4 | Control, in air and on floor | `fig08_v30_tracking.png` |
| 5 | A prediction, then a test | `fig10_ground_load.png` |
| 6 | The fault that defined it | `fig06_encoder_cpr_fault.png` |
| 7 | What the robot cannot see | `fig12_self_occlusion.png` |
| 8 | Maps that would not close | `fig16_correction_traces.png` |
| 9 | The result that decided it | `fig18_invariance.png` |
| 10 | Measuring the input | `fig14_lidar_placement.png` |
| 11 | Choosing between two estimators | `fig19_stage_g.png` |
| 12 | Autonomy: where it stands | `fig21_autonomy_gates.png` |
| 13 | An honest audit | `fig22_layer_audit.png`, or `fig23_defect_taxonomy.png` |
| 14 | Parallel project: UVGI | `fig26_iot_architecture.png` |
| 15 | Gaps, and years 2 to 4 | `fig28_roadmap.png` |
| 16 | Thank you | `fig25_gantt.png` (optional, while taking questions) |

Canva cannot pull these in automatically. Its only ingest path,
`upload-asset-from-url`, needs a file that is already on a public HTTPS URL, and
this repository is private; publishing your files to make one is not an option
worth taking for a drag-and-drop that costs ten minutes.

## Editing the deck

- **The `.pptx`** is a normal PowerPoint file. Edit it in PowerPoint, Keynote or
  Google Slides. To change it from the generator instead, edit the `SLIDES`
  array in `deck_src/build_deck.js` and re-run `node build_deck.js` — but note
  that a rebuild overwrites the file, so do not mix the two on one copy.
- **The Canva design** can be edited in Canva, and Canva also exports it to
  `.pptx`, PDF, PNG, JPG, GIF and MP4. That export is a snapshot: later edits in
  Canva do not reach a file you already downloaded.

## Speaker notes

Every slide carries notes: what to say, what the number means, and what not to
overclaim. Slide 16 lists the four questions most likely to come up and where in
the deck each answer lives.

## Keeping the deck in step with the report

The deck asserts the same numbers as the report. When a figure in
`APS_Report_Draft.md` changes, the matching slide needs the same edit. The
quantities that appear in both:

- 403 / 333 mm wheel radii from centre, 0.561 / 0.491 m yaw coefficients (§5)
- 11–13 % open-loop pair mismatch; 1.2–1.4 % and 3.4–4.0 % closed-loop (§6)
- Ground load +24 % mean, 22.5 / 23.6 / 30.3 / 21.0 per motor (§6, Figure 10)
- 90° self-occlusion wedge, 107 of 430 beams masked (§7)
- Return to mark 0.577 / 0.085 / 0.209 m (§8, Figure 16)
- Cumulative correction 2.80 / 2.85 / 2.86 m (§8, Figure 18)
- Scan churn 74.8–78 %, validity 47.4 % (§8)
- 21.85 m drive: 0.229 m odometry against 0.706 m odometry-plus-SLAM (§8)
- Zero corrections over 698 s and 18.5 m (§8, Figure 19)
- Goals reached in 21–26 s, first round trip 14 August (§9)
- 82 defects across eight categories (§10, Figure 23)
