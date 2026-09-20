# APS seminar deck, 23 September 2026

The deck for the Annual Progress Seminar, built against
[`APS Report Aritra - submitted.pdf`](../APS%20Report%20Aritra%20-%20submitted.pdf),
the version actually handed in. 51 slides, 16:9, speaker notes on every one.

| File | What it is |
|---|---|
| [`NarrowAisleBot_APS_Seminar.pptx`](NarrowAisleBot_APS_Seminar.pptx) | **The deck.** A build artefact. Open it in PowerPoint, Keynote, Google Slides or Canva. |
| `src/content.py` | **Every slide, as data. Edit this, then rebuild.** |
| `src/layouts.py` | The five layouts: title, divider, content, closing, and the primitives under them |
| `src/theme.py` | Type, colour, geometry |
| `src/metrics.py` | Text measurement, so overflow is caught before the file is written |
| `src/build.py` | `python3 src/build.py` |
| `src/qa.py` | `python3 src/qa.py` — measures, renders and checks |
| `assets/*.py` | Figure extraction, figure cropping, photo preparation |
| `assets/fig/`, `assets/slide/`, `assets/photo/`, `build/` | Generated. Not committed; the three scripts above rebuild them. |

The older 16-slide deck in [`../NarrowAisleBot_APS_Seminar.pptx`](../NarrowAisleBot_APS_Seminar.pptx)
was built against the superseded single-objective draft. It is out of date on
both structure and numbers. Use this one.

## How it is put together

Three stories, one after another, in the order the report tells them.

| Slides | |
|---|---|
| 1–3 | Title, the three strands, the five objectives with their status |
| 4–33 | **Strand one, the narrow-aisle robot.** Problem, geometry, platform, control, then ten result slides, then what is open and why |
| 34–41 | **Strand two, environmental monitoring.** Rationale, the unit, three concurrent channels, the control law, what the audit fixed |
| 42–47 | **Strand three, contactless fatigue.** The setting, the hypothesis and the gap, the framework, how it would be falsified |
| 48–51 | What the year established, what is open, the plan, and the report's own closing three statements |

Roughly 45 seconds a slide puts the talk near 38 minutes, which leaves the rest
of the hour for questions.

## What is on a slide and what is in the notes

The slide carries the headline and the numbers. The notes carry the argument,
in the report's own sentences, with the section they come from named. Several
notes also hold material that is not on any slide but that a question will
reach for: the lidar's stationary scatter by range bin, the dynamic-window
controller that was replaced and why, the coverage-denominator qualification,
the reported accuracies of the individual contactless modalities. Read them.

Three habits the report keeps and the deck keeps with it, because they are
what a committee will test:

- **A claim keeps its qualifier.** "Below 1 per cent out to about 10 m" does
  not become "below 1 per cent". "Demonstrated within a live mapping session"
  does not become "demonstrated".
- **Nothing is rounded into agreement.** The rear-right motor sits 0.3 points
  above its predicted band and the slide says so.
- **Where an argument turned out to be wrong, it is still shown.** The
  proportional gain rested on a plant time constant that was out by a factor of
  two; slide 17 is built around that rather than around the answer.

## Images

Every image is a photograph of this robot or a figure from the submitted
report. Nothing is stock, nothing is generated, nothing is from the internet.

- **Figures.** `assets/extract_figs.py` pulls each one out of the submitted PDF
  at 300 dpi and `assets/crop_figs.py` trims its title, its explanatory
  paragraph and its dashed footnote box. Those are written for a reader holding the report; projected,
  they are unreadable texture that competes with the slide heading. The
  untrimmed originals stay in `assets/fig/`. Figure 15, the status board, is
  also split at its own dashed rule into the two halves that become slides 30
  and 31, because at full-slide size its rows cannot be read from the back of a
  room.
- **Photographs.** `assets/prep_photos.py` copies from `docs/robot_photos/` and
  `docs/hardware/photos/`. It applies the EXIF rotation, which the phone writes
  as a tag rather than into the pixels and which PowerPoint ignores, then crops
  to the aspect the slot wants.

Both scripts are re-runnable and neither touches its sources.

## Rebuilding

```bash
pip install python-pptx pillow numpy pymupdf
cd docs/aps_report/seminar_final
python3 assets/extract_figs.py   # figures out of the report PDF, 300 dpi
python3 assets/crop_figs.py      # trim each one for slide use
python3 assets/prep_photos.py    # EXIF-rotate and crop the photographs
python3 src/build.py
python3 src/qa.py
```

Nothing under `assets/fig/`, `assets/slide/`, `assets/photo/` or `build/` is
committed, because all of it regenerates from files already in the repository.

`qa.py` runs three passes. The first measures every bullet block against the
box it will be given, before anything is written, using Caladea and Carlito,
which are metric-compatible with Cambria and Calibri. That one matters most:
python-pptx cannot autofit and cannot wrap, so a paragraph one line too long
does not raise an error, it silently spills over whatever is beneath it. The
second checks no shape has left the slide. The third renders through
LibreOffice and looks for ink in the margins the layout reserves.

It also leaves a PNG of every slide in `build/png/`. Look at them.

## One thing worth knowing about the source PDF

The final PDF supplied on 20 Sep 2026 is not byte-identical to
`../APS Report Aritra - submitted.pdf` in this repository. The figures are the
same, digit for digit, and so is every number quoted in this deck. What differs
is the table-of-contents page numbers, and two figure cross-references in the
body text: Chapter 2's dashboard paragraph and Chapter 3's opening each cite a
figure number one higher than the caption they point at. The captions agree
with each other in both files, and the captions are what this deck's numbering
follows. Worth a look before the report is cited anywhere.

## Fonts

Cambria for headings, Calibri for body. Both ship with Office, so the deck
opens correctly on any machine that has PowerPoint. On Linux, install
`fonts-crosextra-caladea` and `fonts-crosextra-carlito` and the metrics match.

## Before the seminar

- Open the deck on the machine it will be presented from and check slide 12
  (the electronics diagram) and slides 30 and 31 (the status board) from the
  back of the room. They are the three densest figures. If any is unreadable
  from there, say out loud what it shows rather than expecting it to be read.
- Check that the figure colours still mean what the report says they mean:
  orange for the command path, blue for telemetry and perception, red for a
  defect or a gap, green for something fixed or validated, grey for something
  configured but not yet exercised.
