"""Build a plain-language explainer of every figure in the APS report.

For each of the 14 numbered figures: the image itself, then three short
sections — What you're looking at, The numbers in plain English, and Why
it's in the report — written for someone who has not read the report.
"""
import os
from docx import Document
from docx.shared import Pt, Mm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

M = '/tmp/claude-0/-home-user-NarrowAisleBot/3a59de25-0b2f-5e3a-89fe-898a68f9e73b/scratchpad/explainer/hr_extract/word/media'
OUT = '/home/user/NarrowAisleBot/docs/aps_report/Figures Explained.docx'

ACCENT = RGBColor(0x1F, 0x4E, 0x79)   # section-label blue
GREY = RGBColor(0x55, 0x55, 0x55)
RULE = RGBColor(0xCC, 0xCC, 0xCC)

# image file, max width in inches, group heading (starts a new part when it changes)
FIGS = [
    (1, 'image2.jpg', 5.6, 'Part 1 — The robot itself'),
    (2, 'image3.jpg', 6.2, None),
    (3, 'image4.png', 4.4, None),
    (4, 'image5.png', 6.0, None),
    (5, 'image6.png', 6.2, 'Part 2 — The air-quality side project'),
    (6, 'image7.jpg', 3.4, None),
    (7, 'image8.png', 6.2, 'Part 3 — Making the wheels do what they are told'),
    (8, 'image9.png', 5.6, None),
    (9, 'image10.png', 6.2, None),
    (10, 'image11.png', 6.2, None),
    (11, 'image12.png', 6.2, 'Part 4 — Can it see, and can it build a map?'),
    (12, 'image13.png', 6.2, None),
    (13, 'image14.png', 6.2, None),
    (14, 'image15.png', 6.2, 'Part 5 — The scorecard'),
]

TITLES = {
    1: 'The robot as built',
    2: 'Proving the robot agrees with itself about which way is forward',
    3: 'The wiring, laid out as a map',
    4: 'The lopsided wheel layout — the whole idea in one drawing',
    5: 'How the air-quality box is wired together',
    6: 'The air-quality box, built and sitting on a bench',
    7: 'Teaching the controller how much push a motor actually needs',
    8: 'Proof that each wheel’s speed control actually works',
    9: 'How much harder the wheels work once the robot’s weight is on them',
    10: 'Does the robot know where it is, just from counting wheel turns?',
    11: 'The robot has a blind spot, and here is exactly how big it is',
    12: 'Which way of driving actually builds a map, and which wastes time',
    13: 'Three attempts at mapping the lab, side by side',
    14: 'The report card: what is proven, what is not, and why',
}

WHAT = {
1: "A photograph of the finished machine, taken in the lab on 11 August. It is a "
   "rectangular metal chassis about a metre long, riding on four “mecanum” "
   "wheels — wheels with a ring of small rollers around the rim, angled at 45°, "
   "which is what lets the whole robot slide sideways or spin on the spot without "
   "turning the wheels themselves. Standing up out of the middle is a vertical mast "
   "carrying three ultraviolet tubes and the motor for a small cargo arm. The black "
   "disc sitting on top of the battery, just in front of the mast, is the laser "
   "scanner (LiDAR) the robot uses to see the room.",
2: "Four small snapshots side by side. (a) is a top-down photo of the robot with "
   "arrows drawn on by hand: a red arrow pointing to what the team has defined as "
   "“forward,” and a wooden block placed at the true front of the chassis as a "
   "physical reference. (b) is the same instant shown inside the visualisation "
   "software the robot uses — the little red dots are laser hits, and the "
   "coloured lines are the software's own idea of the robot's axes. (c) and (d) are "
   "the first and last frame of a short test where the robot was driven straight "
   "at that block, to check that “forward” in the software is the same "
   "direction as “forward” on the real chassis.",
3: "A colour-coded block diagram of every piece of electronics on the robot and how "
   "they connect: the battery and its voltage converters on one layer, the three "
   "computers (a Raspberry Pi, an ESP32 chip, and a leftover Arduino) on a second "
   "layer, and the motors with their speed sensors on a third. Each wire is coloured "
   "by which voltage it carries, so a stray connection would stand out at a glance.",
4: "An engineering drawing, seen from directly above, of exactly where the four "
   "wheels sit relative to the centre of the robot. It is dimensioned in "
   "millimetres: the front-right and rear-left wheels sit 403 mm from the centre "
   "along the robot's length, while the front-left and rear-right sit only 333 mm "
   "from the centre — a 70 mm difference between the two diagonal pairs.",
5: "A second block diagram, for a completely separate piece of equipment: a box "
   "that watches air quality (CO₂, temperature, humidity, dust, UV light) and "
   "controls a germ-killing UV lamp and a fan. It shows four sensors feeding into "
   "one small computer, which then talks to a home-run server over three different "
   "wireless links at the same time — ordinary Wi-Fi, a long-range radio, and the "
   "mobile phone network — so the server always hears from it by at least one path.",
6: "A plain photograph of that same box, physically built: a metal duct about the "
   "size of a shoebox stretched long, sitting on a lab bench, with a fan visible in "
   "one end and the sensor and control electronics mounted on top in a small "
   "enclosure.",
7: "Two small graphs side by side. The left one plots how much electrical drive "
   "signal (“PWM,” on a scale of 0 to 255) a motor was given against how fast the "
   "wheel actually ended up spinning, with two candidate lines drawn through the "
   "measured points: a plain straight line, and a slightly bent line that starts "
   "a little higher. The right graph shows how far off each candidate line was "
   "from what was actually measured, as a percentage.",
8: "Three stacked graphs, all from one 91-second test with the wheels lifted clear "
   "of the floor. (a) shows one wheel's commanded speed (a thick orange line) laid "
   "directly on top of its actual measured speed (a thin blue line) for the whole "
   "test — they are close enough to be almost indistinguishable. (b) zooms into "
   "the single biggest speed change in that test, sample by sample, so you can see "
   "exactly how the wheel catches up to a new target. (c) shows the gap between "
   "commanded and actual speed for all four wheels, for the whole test, all at once.",
9: "Two bar charts. The left one compares how much drive signal each of the four "
   "wheels needed to hold a given speed in two conditions: wheels spinning freely "
   "in the air (light blue bars) versus the robot sitting on the real floor under "
   "its own weight (dark blue bars) — the dark bars are always taller. The right "
   "chart turns that difference into a percentage increase for each wheel, and "
   "shades in the 10–30 % band that had been written down as a prediction before "
   "this test was ever run.",
10: "Three small maps side by side, each one the path a single test drive traced "
    "out, worked out purely from counting how far each wheel turned (no camera, "
    "laser, or GPS involved). Every drive started and ended at the same physical "
    "spot on the floor, marked with tape; the box under each map states how far "
    "the robot's own estimate of its position was from that real starting mark "
    "when the drive finished.",
11: "Two panels. The left one is a circular, radar-style diagram showing every "
    "direction around the robot that the laser scanner can see, with a red wedge "
    "— roughly a quarter of the full circle, toward the back — marked as blind, "
    "because the robot's own mast and cargo-arm hardware physically sit in the way "
    "of the beam in that direction. The right panel is plain text explaining two "
    "different things that blind spot could cause, and which one the team chose "
    "to prevent.",
12: "A bar chart comparing three different ways of driving the robot around, and "
    "how much new “wall” each style added to the map. Turning the robot in place "
    "at a fixed spot, kept up for over ten minutes, is the first bar; driving a "
    "short curved path while continuously moving forward is the second; a full "
    "lap around the whole room is the third.",
13: "Three floor-plan images, one per test drive, all made from the same cross-"
    "shaped lab room on the same day. Black lines are walls and furniture the "
    "laser actually detected with confidence, grey shading is floor area the "
    "robot never got close enough to see and so knows nothing about, and the thin "
    "coloured line threaded through each map is the literal path the robot drove.",
14: "A long checklist covering every subsystem on the robot — motors, wheel-speed "
    "sensors, the maths behind the wheel layout, position tracking, the laser "
    "map, the path planner, the driving controller, the emergency-stop chain, "
    "matching against a saved map, an added motion sensor, and a memory for named "
    "locations — each marked with a solid green dot (measured and working), a "
    "solid orange dot (working, just slower than hoped), or a hollow circle (not "
    "yet proven), with a short note next to every single one explaining exactly "
    "what evidence backs it up, or exactly why it is not yet checked off.",
}

NUMBERS = {
1: [
 "1.00 m long, 0.36 m wide across the wheels — about the size of a small "
 "suitcase trolley, sized to fit through a warehouse aisle rather than a normal "
 "corridor.",
 "The mast and the laser scanner sit at the same height, in the same horizontal "
 "slice of space. That single fact is the entire reason Figure 11, several pages "
 "later, exists at all.",
],
2: [
 "No measurements here — this figure is a proof, not a data table. The claim it "
 "proves is narrow but important: when the software says the robot moved "
 "“forward,” the robot actually moved toward that wooden block, not sideways "
 "or backward.",
],
3: [
 "Three power rails feeding three different jobs: one steady voltage for the "
 "motors, one for the two onboard computers, one for the sensors.",
 "The caption flags one specific, real mistake this diagram exists to prevent: "
 "the front pair of wheels and the rear pair use different speed-sensor parts "
 "with different wire-colour conventions, and that mismatch has already caused "
 "one wire to be connected wrong during a rebuild.",
],
4: [
 "403 mm vs 333 mm — a 70 mm difference between the two diagonal wheel pairs. "
 "On an ordinary four-wheeled robot those two numbers would be identical.",
 "Two slightly different “width” numbers show up elsewhere in the report: "
 "360 mm, which is a tape measurement of the actual built machine, and 375.4 mm, "
 "which is calculated from the parts on the drawing. They differ by 15.4 mm "
 "because a tape measure and a CAD drawing are never perfectly identical things "
 "— the report is explicit that the 360 mm tape figure is the one every real "
 "test result is measured against.",
],
5: [
 "Three communication paths running at once: Wi-Fi every 5 seconds, a long-"
 "range radio every 30 seconds, and a text message on alert. All three run all "
 "the time, rather than one being a backup that only switches on if another "
 "fails.",
],
6: [
 "No numbers on this one either — it exists purely to show that the diagram in "
 "Figure 5 is a real, physically assembled device and not just a plan on paper.",
],
7: [
 "A plain straight-line rule under-predicts how much push a motor needs at low "
 "speed, because it ignores the fact that every motor needs a small extra "
 "“kick” just to overcome friction and start turning at all.",
 "The two-part rule used instead — a fixed kick plus a proportional term — "
 "matches the measured points to within about 8 %, and to within 2.3 % for the "
 "two most trustworthy measurements.",
],
8: [
 "The wheel reaches within 5 % of a newly commanded speed in 0.20 seconds, "
 "overshoots that target by 3.5 %, then settles down to sitting only 0.003 rad/s "
 "off the commanded value — a genuinely tiny error.",
 "Worth knowing: that 0.20-second figure includes some time the commanded speed "
 "itself was still ramping up to its new value, so it is not a pure measure of "
 "how fast the wheel alone reacts — a fair question to expect if this graph "
 "comes up.",
],
9: [
 "24 % more drive signal needed, on average, once the robot's full weight is on "
 "the wheels — and this was predicted to land somewhere between 10 % and 30 % "
 "before the test was run, then checked against that prediction rather than "
 "explained afterward.",
 "Worth knowing: this 24 % figure comes from one test session. Two later "
 "sessions, on different patches of the same lab floor, gave smaller increases "
 "— 14 % and then 3 % — which shows the exact size of the effect depends on "
 "which bit of floor the robot happens to be sitting on, not only on its weight.",
],
10: [
 "The three drives closed to within 19 mm, 28 mm, and 96 mm of their true "
 "starting spot, over routes of 8.00 m, 9.61 m, and 10.61 m — that is 0.23 %, "
 "0.29 %, and 0.91 % of the distance actually travelled.",
 "The longest of the three, which also involved the most turning, had the "
 "largest error — a pattern the report follows up on later: turning seems to "
 "cost more positioning accuracy than straight driving does.",
],
11: [
 "The blind wedge covers about 90 degrees — a quarter of the full circle — and "
 "blocks 107 of the 430 individual laser readings the scanner takes on each spin.",
 "The fix chosen was simply to tell the software to throw those 107 readings "
 "away before they reach the mapping or navigation code, rather than trying to "
 "make sense of them.",
],
12: [
 "Ten and a half minutes of spinning in place produced only 2.1 m worth of new "
 "wall on the map. A 111-second curved path while still moving forward produced "
 "77.2 m — 88 % of what a full lap of the room eventually produces, in under a "
 "fifth of the time a full lap takes.",
],
13: [
 "All three drives returned successfully to within a few centimetres of their "
 "starting mark, and the wall shapes they did manage to see agree with each "
 "other and with the real room.",
 "The grey “never observed” area covers the majority of every map — not "
 "because the laser or the software failed, but because the lab's open floor "
 "space is small enough that the robot simply cannot drive far enough to see "
 "the rest of the room in one loop.",
],
14: [
 "Seven items are fully green: motor control, speed sensing, the maths for the "
 "lopsided wheel layout, position tracking, matching where the robot thinks it "
 "is against where it actually is, the touchscreen control panel, and the yaw-"
 "consistency check. Three are orange: the path planner, the driving controller, "
 "and the emergency-stop chain all work correctly but run a bit slower than the "
 "team originally hoped for, because the onboard computer is doing a lot at "
 "once.",
 "Five are still hollow, and three of those five share one root cause stated "
 "plainly on the figure itself: the lab is too small to drive the loop these "
 "tests need. That is not a flaw in the robot — it is a flaw in the available "
 "test space, and the figure says so rather than hiding it inside a vague "
 "“future work” line.",
],
}

WHY = {
1: "This is the reference photo for the whole report — the physical object every "
   "later measurement is a measurement of. It is also doing quiet extra work: by "
   "showing the mast sitting right next to the laser scanner, it sets up the "
   "self-occlusion problem covered in Figure 11 before the report has even said "
   "the word “occluded.”",
2: "Small mistakes about which direction is “forward” sound trivial, but they are "
   "exactly the kind of error that causes a robot to drive the wrong way "
   "confidently. This figure is the paper trail proving the convention was "
   "settled by an actual physical test rather than assumed and hoped for.",
3: "A generic wiring reference for this kind of robot would get two things wrong "
   "here specifically: it would assume identical speed sensors on every wheel, "
   "and it would assume a different voltage-conversion part than what is "
   "actually bolted in. This diagram is drawn from the real, as-built machine "
   "for exactly that reason — so the next person who opens the electronics box "
   "does not repeat a mistake that has already happened once.",
4: "This is the single idea the entire first half of the thesis is built around. "
   "Ordinary robots with these sideways-sliding wheels put all four wheels at "
   "the corners of a plain rectangle, which forces the whole machine to be as "
   "wide as that rectangle. Moving the two diagonal wheel-pairs to different "
   "distances from the centre — what the report calls “asymmetric” — lets the "
   "robot keep all the sideways-sliding ability while being built narrower, "
   "which matters because the entire point of the project is fitting into a "
   "warehouse aisle. This drawing is simply the proof of exactly how that idea "
   "was actually built, in millimetres.",
5: "This documents the second, separate goal of the project: an air-quality box "
   "that reacts to what it actually measures instead of running a UV lamp on a "
   "blind timer. The decision to run three wireless channels simultaneously, "
   "rather than have two sit idle as backups, is explained here too — in a real "
   "network failure, the first thing that usually breaks is your ability to "
   "detect that something broke, so waiting to detect a failure before "
   "switching to a backup channel is often too late.",
6: "The same logic as Figure 1: a diagram is a plan, a photograph is proof the "
   "plan became a real object. This also heads off a possible mix-up — the "
   "robot itself carries its own separate UV lighting for a different job "
   "(visible on the mast in Figure 1), and this caption is explicit that the "
   "two UV systems are unrelated pieces of equipment.",
7: "Every wheel on the robot is driven by this exact calibration. If a straight-"
   "line rule had been used instead, wheels would be under-powered at low "
   "speeds, and the report notes elsewhere that this specific problem caused an "
   "early version of the robot to stutter when trying to slide sideways, "
   "because one wheel in a matched pair was quietly getting less push than its "
   "partner for the same commanded speed.",
8: "Nothing else in the report means anything if the wheels do not reliably do "
   "what they are told — every distance driven, every position estimate, every "
   "map is built on top of this. This figure is the foundational proof that the "
   "lowest, most basic layer of the whole system is solid, checked before "
   "anything more complicated was layered on top of it.",
9: "The speed controller in Figure 8 was tuned with the wheels in the air. "
   "Without knowing how much extra push the real floor demands, that same "
   "controller would quietly fall behind its commanded speed the moment the "
   "robot actually starts driving somewhere loaded, because it would be under-"
   "powering every wheel by roughly a quarter.",
10: "This is the cheapest, simplest way the robot has of estimating its own "
    "position — no camera, no laser, just counting wheel turns — and this figure "
    "establishes that it is accurate to under 1 % of distance travelled over "
    "these short routes. That number then becomes the yardstick the rest of the "
    "report measures every fancier positioning method against, including one "
    "later method (adding laser-based correction) that this yardstick reveals "
    "actually makes things worse rather than better.",
11: "Before this was diagnosed, the laser could in principle mistake its own "
    "mast for a permanent wall stuck to the robot, appearing in the exact same "
    "spot no matter which way the robot turned — the software equivalent of an "
    "invisible wall glued to the machine. This figure documents both the size "
    "of the problem and the fix: simply telling the software to ignore that "
    "wedge of readings entirely, before it ever reaches the mapping code.",
12: "This one changed an actual, everyday habit rather than any piece of "
    "hardware or code. The commissioning routine used to have the robot pause "
    "and spin at every corner to “look around” — a very natural thing to try, "
    "and this chart is the evidence that it barely works with this particular "
    "mapping software. The team changed the driving procedure afterward: keep "
    "the robot moving through every turn instead of stopping to spin, because "
    "that is what the software actually rewards. It is presented as one of the "
    "most valuable findings of the whole project precisely because the fix was "
    "free — no new part, no new code, just driving differently.",
13: "This figure makes the report's central mapping problem visible at a glance "
    "rather than requiring a paragraph of explanation: the maps are incomplete "
    "not because anything on the robot is broken, but because the lab does not "
    "offer enough open floor for the robot to drive a big enough loop to see "
    "the rest of the room. One of four pass/fail rules set in advance for "
    "judging a map “good enough,” the amount of unobserved area, is the one "
    "rule all three maps fail here, and this figure is the honest reason why.",
14: "This is the figure to remember above all the others. Instead of a vague "
    "closing claim that “the robot mostly works,” it grades every single claim "
    "in the report by the actual evidence behind it, and for everything not yet "
    "proven it states the specific reason rather than leaving a silent gap. A "
    "reader — or an examiner — can see the entire state of the project in one "
    "look, and see that most of what remains unfinished has one shared cause "
    "rather than being a scattered list of separate failures.",
}


def set_font(style, name, size, bold=False, color=None):
    style.font.name = name
    style.font.size = Pt(size)
    style.font.bold = bold
    if color is not None:
        style.font.color.rgb = color
    rpr = style.element.get_or_add_rPr()
    from docx.oxml import OxmlElement as OE
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OE('w:rFonts')
        rpr.append(rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:cs'):
        rf.set(qn(a), name)


def add_rule(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    pPr = p._p.get_or_add_pPr()
    border = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '4')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), 'CCCCCC')
    border.append(bottom)
    pPr.append(border)


doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Mm(210), Mm(297)
sec.left_margin = sec.right_margin = Mm(22)
sec.top_margin = sec.bottom_margin = Mm(20)

st = doc.styles['Normal']
set_font(st, 'Calibri', 11)
st.paragraph_format.space_after = Pt(8)
st.paragraph_format.line_spacing = 1.15

h1 = doc.styles['Heading 1']
set_font(h1, 'Calibri', 20, bold=True, color=RGBColor(0x11, 0x11, 0x11))
h1.paragraph_format.space_before = Pt(0)
h1.paragraph_format.space_after = Pt(4)

h2 = doc.styles['Heading 2']
set_font(h2, 'Calibri', 15, bold=True, color=ACCENT)
h2.paragraph_format.space_before = Pt(26)
h2.paragraph_format.space_after = Pt(2)
h2.paragraph_format.keep_with_next = True

h3 = doc.styles['Heading 3']
set_font(h3, 'Calibri', 13, bold=True, color=RGBColor(0x22, 0x22, 0x22))
h3.paragraph_format.space_before = Pt(14)
h3.paragraph_format.space_after = Pt(6)
h3.paragraph_format.keep_with_next = True


def label(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text.upper())
    r.bold = True
    r.font.size = Pt(9.5)
    r.font.color.rgb = ACCENT
    r.font.name = 'Calibri'


def body(doc, text):
    p = doc.add_paragraph(text)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def bullets(doc, items):
    for it in items:
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(6)
        p.add_run(it)


# ---- title
p = doc.add_paragraph()
p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(2)
r = p.add_run('Every Figure in the APS Report, Explained')
r.bold = True
r.font.size = Pt(26)
r.font.name = 'Calibri'

p = doc.add_paragraph()
p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(20)
r = p.add_run('What each graph and diagram shows, in plain language, and why it earned a place in the report')
r.italic = True
r.font.size = Pt(12.5)
r.font.color.rgb = GREY
r.font.name = 'Calibri'

body(doc,
     'The report has fourteen figures. Some are photographs proving a piece of '
     'hardware actually exists; some are diagrams of how something is wired '
     'together; most are graphs of a real measurement taken off the robot. This '
     'document goes through every one of them in the order they appear in the '
     'report, and for each asks the same three questions: what am I looking at, '
     'what do the numbers on it actually mean, and why does this particular '
     'picture matter enough to be in the report at all.')
body(doc,
     'Nothing here changes or challenges anything in the report itself — it is a '
     'companion for reading it, written for viva preparation and for anyone '
     'coming to the figures without the surrounding technical background.')

doc.add_page_break()

current_group = None
for num, img, width_in, group in FIGS:
    if group and group != current_group:
        doc.add_paragraph()
        gp = doc.add_paragraph()
        gp.paragraph_format.space_before = Pt(0)
        gp.paragraph_format.space_after = Pt(4)
        gr = gp.add_run(group)
        gr.bold = True
        gr.font.size = Pt(17)
        gr.font.color.rgb = RGBColor(0x0A, 0x0A, 0x0A)
        gr.font.name = 'Calibri'
        add_rule(doc)
        current_group = group

    doc.add_paragraph(f'Figure {num} — {TITLES[num]}', style='Heading 2')

    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(10)
    p.add_run().add_picture(f'{M}/{img}', width=Inches(width_in))

    label(doc, 'What you’re looking at')
    body(doc, WHAT[num])

    label(doc, 'The numbers, in plain English')
    bullets(doc, NUMBERS[num])

    label(doc, 'Why it’s in the report')
    body(doc, WHY[num])

    if num != 14:
        doc.add_page_break()

os.makedirs(os.path.dirname(OUT), exist_ok=True)
doc.save(OUT)
print('wrote', OUT)
print('paragraphs', len(doc.paragraphs))
