# How `APS report Aritra.docx` was built

The submitted PDF of 17 Sep 2026 was produced in Word, and that `.docx` is not
in this repository. To apply the corrections from
`docs/APS_Report_PDF_Audit_2026-09-17.md` without losing the layout, the
document was rebuilt from the PDF rather than retyped.

```
extract.py        reads the PDF into blocks.json: every text line with its
                  font, size, position and inline bold/italic runs
build_report.py   assembles those lines into paragraphs, applies the edits,
                  and writes the .docx
blocks.json       the extraction, so the build runs without the source PDF
frontmatter.json  acknowledgement and undertaking, pulled from pages 2 and 3
toc.json          the contents entries and their page numbers
figures_from_pdf/ the 14 figures and the institute crest, lifted from the PDF
                  byte for byte, so nothing is recompressed a second time
```

Rebuild with `python3 build_report.py` (needs `python-docx` and `pdfminer.six`).

## Layout, measured off the PDF rather than guessed

A4, 25.4 mm margins. Body Times New Roman 12, justified, single line spacing,
9 pt after a paragraph. Chapter headings Calibri Bold 16, section headings
Calibri Bold 14. Captions Times New Roman Italic 9, justified, under a centred
label line. Tables carry a rule above the header, one below it and one under
the last row, with no vertical or interior rules, and repeat their header row
across a page break. References are Cambria 12 with a 0.5 in hanging indent.
Chapters are separated by a blank line rather than a page break, which is what
the original does, and the four equation blocks are rebuilt as native Word
equations rather than as flattened text.

## The edits

Each one is a `(count, find, replace)` triple in `build_report.py`, and the
count is asserted, so an edit that fails to match stops the build instead of
passing silently. They are the four fixes of the audit's §5 plus the three
smaller ones it defers.

## What the build is checked against

1. Word-level diff between the original PDF and the rebuilt one. Nothing
   differs except the intended edits, the page numbers and the reading order
   inside tables.
2. Both old and new wordings are searched for by hand: 13 removals confirmed
   gone, 16 insertions confirmed present.
3. Every chapter and section heading is confirmed to fall on the same page as
   in the original, 35 of 35, and the document is 37 pages, as the original is.
4. Every page number in the contents is checked against where its heading
   actually lands.

The rendering used for those checks came from LibreOffice, which substitutes
metric-compatible fonts for Times New Roman, Calibri and Cambria. Line breaks
in Word will be very close but not guaranteed identical.

## Two deliberate departures from the original

**Page numbers.** The original prints none, while its contents page cites page
numbers throughout. A footer with a centred page number was added so the
contents point at something. Delete the footer if it is unwanted.

**The contents is static text, not a field.** The page numbers are the
original's, and they were verified against the rebuilt document. If the text is
edited further, check them again or replace the block with a Word TOC field.
