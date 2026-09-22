# APS study guide

The study companion to the submitted APS report. 93 pages, Word format,
written for the night before rather than for a reader who already knows the
vocabulary. Every idea appears twice: once in plain words with an analogy, once
with the real numbers from this robot.

| File | What it is |
|---|---|
| [`NarrowAisleBot_APS_Study_Guide.docx`](NarrowAisleBot_APS_Study_Guide.docx) | **The document.** A build artefact. Open it in Word, Pages or Google Docs. |
| `src/c*.js` | **The content, one file per part. Edit these, then rebuild.** |
| `src/style.js` | Type, colour, and the building blocks: boxes, tables, equations, code, figures |
| `src/build.js` | `node src/build.js` |
| `build/` | The rendered PDF. Not committed. |

`docs/aps_report/seminar_final/` holds the slide deck, which shares this
document's numbers and its colour language.

## What is in it

| Part | |
|---|---|
| 1 | The problem, why mecanum, why asymmetric, what was inherited versus built, the five objectives with their honest status |
| 2 | **Every piece of hardware and why it is there**, including what is deliberately absent |
| 3 | Kinematics, the two lever arms, the free yaw observable and why it is worth less than it looks |
| **4** | **Feedforward and PID from first principles.** What P, I and D each do, what each value does in real units, the anti-windup, the slew limiter, the safety trips |
| **5** | **Where the gain values came from.** Direct synthesis worked through, and the honest story of the proportional gain whose derivation collapsed |
| 6 | Odometry, the photogrammetry result, and the full argument for having no inertial sensor |
| 7 | The lidar: what was measured rather than assumed, and the self-occlusion wedge |
| **8** | **SLAM: theory, then every constraint**, each with its justification |
| **9** | **Navigation: theory, then every constraint**, same treatment |
| 10 | **All 21 report figures**, embedded, each with what is plotted, what it shows, the line to say, and the question it invites |
| 11 | Strand two, environmental monitoring |
| 12 | Strand three, contactless fatigue |
| 13 | The question bank: three tiers plus the four hostile questions |
| 14 | The corridor sheet, to read in the ten minutes before going in |

## The three rules it is written around

These are the report's own habits, and they are what a panel actually marks.

- **Every number arrives with its evidence grade.** Measured on this robot,
  checked against an independent implementation, reasoned but not tested, or
  not yet done. Saying which one is worth more than the number.
- **Qualifiers survive.** "Below 1 per cent out to about 10 m" never shortens
  to "below 1 per cent". "Demonstrated inside a live mapping session" never
  shortens to "demonstrated".
- **Failures are results.** Scan matching making the pose worse, the
  proportional-gain argument collapsing, the coverage criterion failing: each
  has a diagnosed mechanism, and each is stronger delivered than discovered.

## Where the material comes from

The report is the spine. The detail the report compresses comes out of this
repository, and that is most of what makes this document longer than the
report: `docs/PID_Calibration.md` for where every gain came from and the sweep
that kept the shipped one, `docs/SLAM_Theory.md` and `docs/Navigation_Theory.md`
for the algorithm choices and the papers behind them, `system/*.yaml` for the
deployed configuration and the measured reason against each value that was
moved off stock, `aislebot_esp32.ino` for the loop as it actually runs, and
`docs/Research_Journal.md` for the faults as they were found.

Every number in the document was checked back against the report text or against
those files by script. The handful that do not match either are arithmetic shown
in the open (16,000,000 divided by 558,792, for instance) or figures quoted with
a trailing zero.

## Rebuilding

```bash
cd docs/aps_study
npm install docx          # only the first time
node src/build.js
```

To look at it:

```bash
soffice --headless --convert-to pdf --outdir build NarrowAisleBot_APS_Study_Guide.docx
```

Word will ask to update the table of contents on first open, or right-click it
and choose "Update field". docx-js writes the field but cannot compute page
numbers.

## Conventions the source files keep

- `**bold**`, `_italic_` and `` `code` `` work inside any string. Nothing else
  is markdown.
- Boxes carry meaning by colour: `analogy` blue, `good` green for something to
  say out loud, `warn` amber for a qualification, `bad` red for a defect or a
  trap. Same language as the report and the deck.
- **No em dashes**, per the author's writing rules. Commas, colons and
  parentheses instead.
- `figure('fig09', caption)` pulls a report figure out of
  `docs/aps_report/seminar_final/assets/slide/`, so the images regenerate from
  the report PDF rather than being copied in. Run that folder's
  `assets/extract_figs.py` and `assets/crop_figs.py` first on a fresh clone, or
  the figure calls print a placeholder line instead.
