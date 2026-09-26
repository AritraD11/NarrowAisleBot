# APS Report — first year, submitted and presented

The first Annual Progress Seminar was held 23 Sep 2026. The candidate qualified.
This folder holds what was actually submitted and presented, plus the sources
that built them. Everything from the drafting process that led up to
submission is kept in `archive/`, not deleted, since the report's own working
history is still worth being able to trace.

## What to open

| File | What it is |
|---|---|
| [`APS Report Aritra - submitted.pdf`](APS%20Report%20Aritra%20-%20submitted.pdf) | **The report, as submitted.** The literal PDF handed in. |
| [`seminar_final/`](seminar_final/) | **The deck.** `NarrowAisleBot_APS_Seminar.pptx` is the last build from this folder's pipeline; see its own README for the narrative arc and rebuild instructions. If a copy was hand-edited in PowerPoint just before presenting, that copy is the one actually presented — check `seminar_final/README.md` for whichever is current. |
| [`aps_study/`](../aps_study/) | The 93-page study guide built alongside the deck, same source-of-truth discipline (`src/`, not the `.docx` directly). |
| [`final_src/`](final_src/) | How `APS report Aritra.docx` (in `archive/`) was rebuilt from the submitted PDF plus the `Audit_2026-09-17` corrections. Read its own README before touching it. |
| [`figure_src/`](figure_src/) | The scripts that generate the report's own figures from bench/field data. Still the source of truth for regenerating a figure — nothing here is superseded. |
| [`figures/`](figures/) | The rendered figures, PNG at 300 dpi. |

## `archive/` — superseded, kept for provenance

Draft history leading up to the 15–22 Sep 2026 submission and seminar. None of
it is current; none of it should be edited or resubmitted. Kept because a
report's revision history is evidence of its own kind, and because two of the
docx variants (`APS report Aritra.docx`, the `final_src`-built corrected copy,
and `Figures Explained.docx`, a plain-language walkthrough of every figure) are
still useful reading even though they are not the submitted file.

| File | What it was |
|---|---|
| `APS_Report_Draft.md` / `.docx` | The original single-objective draft structure, superseded 15 Sep by the three-objective restructure. |
| `APS_Report_Draft_v2.md` | The chosen three-objective draft, in progress before the final edited-report and restructure passes. |
| `APS Report Aritra - restructured.docx` | An intermediate restructuring pass, before the version actually submitted. |
| `APS report Aritra - high resolution.docx` | A high-resolution figure pass on the same draft lineage. |
| `APS report Aritra.docx` | The corrected docx `final_src/` rebuilds from the submitted PDF; the editable counterpart to the PDF if the report text needs touching again. |
| `Figures Explained.docx` | A plain-language explainer for every figure in the report — supplementary, not a report variant. |
| `NarrowAisleBot_APS_Seminar_v1_16slide.pptx` | The first seminar deck, 16 slides, built against the single-objective draft. Superseded by `seminar_final/`. |
| `SEMINAR_DECK.md` | How the v1 16-slide deck was put together. Superseded by `seminar_final/README.md`. |
| `deck_src/` | The v1 deck's JS/PowerPoint generator (`build_deck.js`), plus a standalone gains-slide builder from seminar prep. Superseded by `seminar_final/src/` (Python/python-pptx). |
| `v2_src/` | The build pipeline for `APS_Report_Draft_v2.md`. Superseded once the report was submitted. |

## Related, one level up

- [`../APS_Seminar_QA_Log_2026-09-21.md`](../APS_Seminar_QA_Log_2026-09-21.md) — seminar prep Q&A: the PID/feedforward derivation walked through conversationally, an informal pose-estimation on/off check against the dashboard, and the full chain behind why no commissioning map has been accepted. Defers to the report and journal wherever they disagree.
- [`figure_src/f_pidloop_corrected.py`](figure_src/f_pidloop_corrected.py) → [`figures/fig33_pid_loop_corrected.png`](figures/fig33_pid_loop_corrected.png) — a corrected-wiring variant of the PID/feedforward block diagram, kept as reference; not currently placed in the submitted report or the deck.
