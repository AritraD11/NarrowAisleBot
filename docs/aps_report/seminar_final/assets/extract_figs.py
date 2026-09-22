"""Pull the report's 21 figures out of the submitted PDF at 300 dpi.

    python3 assets/extract_figs.py [path/to/report.pdf]

The default source is the final submitted PDF as the author supplied it on
20 Sep 2026. Note that it is not byte-identical to
`docs/aps_report/APS Report Aritra - submitted.pdf` in this repository: the two
differ in the table-of-contents page numbers and in two figure cross-references
in the body text (Chapter 2's dashboard paragraph and Chapter 3's opening both
cite a figure number one higher than the caption they point at). The captions
themselves agree, and the captions are what the numbering below follows, so
the extraction is the same either way.

Output lands in assets/fig/ and is not committed: every figure comes out
byte-identical from either PDF, so the repository's own copy regenerates it.
assets/crop_figs.py then turns it into the slide versions in assets/slide/.
"""
import os
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(HERE, 'fig')
DEFAULT_PDF = os.path.abspath(os.path.join(
    HERE, '..', '..', 'APS Report Aritra - submitted.pdf'))

# report figure number -> (0-based page index, index of the image on that page)
FIGURES = {
    1:  (10, 0), 2:  (11, 0), 3:  (12, 0), 4:  (13, 0), 5:  (16, 0), 6:  (17, 0),
    7:  (19, 0), 8:  (19, 1), 9:  (23, 0), 10: (24, 0), 11: (25, 0), 12: (26, 0),
    13: (27, 0), 14: (27, 1), 15: (32, 0), 16: (36, 0), 17: (38, 0), 18: (40, 0),
    19: (42, 0), 20: (45, 0), 21: (46, 0),
}


def main(src=DEFAULT_PDF):
    os.makedirs(DST, exist_ok=True)
    doc = pymupdf.open(src)
    for n, (page_i, img_i) in sorted(FIGURES.items()):
        page = doc[page_i]
        xref = page.get_images(full=True)[img_i][0]
        rect = page.get_image_rects(xref)[0]
        pix = page.get_pixmap(clip=rect, dpi=300)
        out = os.path.join(DST, 'fig%02d.png' % n)
        pix.save(out)
        print('fig%02d  p%-3d %4d x %4d' % (n, page_i + 1, pix.width, pix.height))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF)
