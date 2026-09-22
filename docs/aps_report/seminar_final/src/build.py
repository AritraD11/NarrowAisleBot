#!/usr/bin/env python3
"""Build NarrowAisleBot_APS_Seminar.pptx from src/content.py.

    python3 docs/aps_report/seminar_final/src/build.py

The .pptx is a build artefact. Edit content.py and rebuild rather than editing
the deck, or the two diverge and the generator becomes the stale copy.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pptx import Presentation
from pptx.util import Inches

import layouts
from content import SLIDES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..', 'NarrowAisleBot_APS_Seminar.pptx'))


def build(path=OUT):
    prs = Presentation()
    prs.slide_width = Inches(layouts.SW)
    prs.slide_height = Inches(layouts.SH)

    for i, s in enumerate(SLIDES, start=1):
        kind = s.get('layout', 'content')
        if kind == 'title':
            layouts.title_slide(prs, s)
        elif kind == 'divider':
            layouts.divider(prs, s, i)
        elif kind == 'closing':
            layouts.closing(prs, s, i)
        elif kind == 'kinematics':
            layouts.kinematics_slide(prs, s, i)
        else:
            layouts.content(prs, s, i)

    prs.save(path)
    size = os.path.getsize(path) / 1e6
    print('%d slides  ->  %s  (%.1f MB)' % (len(SLIDES), os.path.relpath(path, os.getcwd()), size))
    return path


if __name__ == '__main__':
    build()
