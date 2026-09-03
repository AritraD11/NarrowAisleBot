# APS Report — working folder

First-year Annual Progress Report. The draft is kept here in Markdown so it can
be edited continuously and converted to a submission format on the day it is
needed, rather than being re-typed into a word processor and then diverging from
the project record.

| File | What it is |
|---|---|
| [`APS_Report_Draft.md`](APS_Report_Draft.md) | The report. **Edit this one.** |
| [`APS_Report_Draft.docx`](APS_Report_Draft.docx) | Built from the Markdown, all 28 figures embedded, table of contents included. Download and open. Regenerate it after every edit with the command below rather than editing it directly, or the two will diverge. |
| [`figures/`](figures/) | 28 figures, PNG at 300 dpi, numbered to match the in-text figure numbers |
| [`figure_src/`](figure_src/) | The scripts that generate every figure |
| [`SEMINAR_DECK.md`](SEMINAR_DECK.md) | The Canva seminar deck: design ID, which figure belongs on which slide, and the numbers the deck shares with the report |

## Editing conventions

- **Figure numbering.** `figures/figNN_*.png` matches **Figure NN** in the text.
  If a figure is inserted or removed, renumber both together, or the next person
  to read this will spend an hour finding out why they disagree.
- **`[CONFIRM]` markers.** Every place the report states something the
  repository cannot supply. Search for the string before submitting; none should
  survive into the final version.
- **Numbers.** Every quantitative claim traces to a file in this repository or a
  DOI in §12. If a number changes on the robot, change it here too, and prefer
  regenerating the figure to editing the caption.

## Regenerating the figures

Needs `numpy` and `matplotlib`. Nothing else; no LaTeX installation is required.

```bash
pip install numpy matplotlib
for f in docs/aps_report/figure_src/f_*.py; do python3 "$f"; done
```

The scripts read the bench telemetry in `data/bench_logs/`, the field pose logs
in `data/field_runs/`, and the photographs in `docs/robot_photos/` directly, so
the plots are regenerated from source data rather than being static images that
can silently go stale. Paths resolve relative to the script's own location, so
they run from anywhere.

Two figures are computed rather than transcribed, because they carry claims:
**Figure 10** recomputes the ground-load feedforward increase from the 5 and
6 August telemetry logs, and **Figure 16** replots the map-to-odom correction
traces from the three field runs. Both agree with the journal to the digit,
which is the point of regenerating them rather than screenshotting.

`style.py` holds the shared colour language, and it is worth keeping consistent:
orange for the command path, blue for telemetry and perception, red for a defect
or a gap, green for something fixed or validated, grey for something configured
but not yet exercised. The first caption in the report states this so a reader
does not have to infer it.

## Converting for submission

```bash
# Word, keeping the figures
pandoc APS_Report_Draft.md -o APS_Report.docx --resource-path=.

# PDF via LaTeX, with a table of contents and numbered sections
pandoc APS_Report_Draft.md -o APS_Report.pdf --resource-path=. \
       --toc --number-sections -V geometry:margin=25mm
```

The Word conversion is verified: it produces a roughly 9 MB file with all
28 figures embedded. The PDF route additionally needs a LaTeX engine
(`texlive-latex-recommended` plus `texlive-fonts-recommended` is enough), or
`--pdf-engine=weasyprint` to avoid LaTeX entirely.

The maths uses `$...$` and `$$...$$`, which both routes handle. Wide tables
convert cleanly to Word; for PDF, `--columns=100` helps if any overflow the
margin.

If the department expects the IIT Bombay LaTeX report class, the Markdown
converts to `.tex` with `pandoc -s -o body.tex` and the result can be dropped
into that template's body.

## Before submitting

- [ ] Confirm the APS deadline and cycle with the Academic Office
- [ ] Download the current APS form from the ASC portal and check its fields
      against what this report states
- [ ] Read a recent accepted report from the department for format and length
- [ ] Agree with the supervisor how much of §10 to include
- [ ] Consult IRCC on disclosure if a patent filing is contemplated
- [ ] Recover the full bibliographic details for references 1–4
- [ ] Fill in the parallel project's dates and effort fraction (§9.3)
- [ ] Resolve every `[CONFIRM]` marker
- [ ] Have someone who is not the author read it
