// Standalone build for ONE replacement slide: "Where the gains came from",
// merging the old slides 14 and 15 into one, no figure. Does NOT touch
// build_deck.js or the live .pptx, since that file has already diverged
// from the generator (hand-added slides not in the SLIDES array) and a
// full rebuild would overwrite them. This produces a single-slide .pptx
// with identical fonts/colours/geometry, to paste into the real deck.
//
//   node build_gains_slide.js
//
// Output: ./gains_slide_standalone.pptx

const pptxgen = require('pptxgenjs');

const INK = '1A1A1A';
const ACCENT = '1F4E79';
const MUTED = '5A5A5A';
const PAPER = 'FFFFFF';
const TITLE_FONT = 'Cambria';
const BODY_FONT = 'Calibri';

const W = 13.333, H = 7.5;
const M = 0.55;
const TITLE_Y = 0.42;
const BAND_Y = 1.5;
const COL_W = W - 2 * M;

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';

const slide = pres.addSlide();
slide.background = { color: PAPER };

slide.addText('Where the gains came from', {
  x: M, y: TITLE_Y, w: W - 2 * M, h: 0.8,
  fontFace: TITLE_FONT, fontSize: 32, bold: true, color: INK,
  align: 'left', valign: 'middle', margin: 0, isTextBox: true,
});
slide.addShape('line', {
  x: M, y: TITLE_Y + 0.82, w: 1.0, h: 0,
  line: { color: ACCENT, width: 2.5 },
});

const cards = [
  { head: 'The feedforward terms, fitted',
    body: 'Kff ≈ 38 PWM per rad/s and Kstat ≈ 8 PWM, both fit from three independent bench campaigns, wheels free, no load. The static term exists because a straight line through the origin cannot reproduce breakaway friction.' },
  { head: 'The PID terms, computed then checked',
    body: 'Ki = 250 from direct synthesis on the fitted plant gain, not tuned by hand. Kp = 45 and Kd = 0.5 were re-derived from a later, measured plant time constant, then verified by sweeping the recomputed values against the shipped ones on real hardware — the original gains won and were kept.' },
];

let y = BAND_Y;
for (const card of cards) {
  slide.addText(card.head, {
    x: M, y, w: COL_W, h: 0.36,
    fontFace: BODY_FONT, fontSize: 16, bold: true, color: ACCENT,
    align: 'left', valign: 'top', margin: 0, isTextBox: true,
  });
  slide.addText(card.body, {
    x: M, y: y + 0.42, w: COL_W, h: 1.7,
    fontFace: BODY_FONT, fontSize: 15, color: INK,
    align: 'left', valign: 'top', lineSpacingMultiple: 1.2,
    margin: 0, isTextBox: true,
  });
  y += 2.55;
}

slide.addText('THE NARROW AISLE ROBOT', {
  x: W - M - 3.0, y: 0.25, w: 3.0, h: 0.3,
  fontFace: BODY_FONT, fontSize: 9, color: MUTED,
  align: 'right', margin: 0, isTextBox: true,
});
slide.addText('Annual Progress Seminar · Aritra Das · 25D0074 · IIT Bombay', {
  x: M, y: H - 0.5, w: 8.0, h: 0.3,
  fontFace: BODY_FONT, fontSize: 9, color: MUTED,
  align: 'left', margin: 0, isTextBox: true,
});

slide.addNotes(
  'Five gains, two families. Kff and Kstat came from fitting three bench ' +
  'campaigns to a two-term friction model. Ki came from direct synthesis, ' +
  'computed once from the fitted plant gain and a chosen closed-loop time ' +
  'constant, not searched. Kp and Kd were both re-derived after a later ' +
  'bench test finally measured the plant time constant directly, at half ' +
  'the value that had been assumed; the recomputed gains were swept ' +
  'against the shipped ones on real hardware and lost on overshoot, so ' +
  'the original values were kept, confirmed rather than changed.'
);

pres.writeFile({ fileName: 'gains_slide_standalone.pptx' }).then(() => {
  console.log('wrote gains_slide_standalone.pptx');
}).catch((e) => { console.error(e); process.exit(1); });
