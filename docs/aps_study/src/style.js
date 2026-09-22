// Shared building blocks for the APS study guide.
//
// Everything in the document is assembled from these, so the look is set in
// one place. A4, 0.75 in margins, Cambria headings and Calibri body to match
// the seminar deck. Colours carry the report's own meaning: green for
// something measured, amber for something open, red for a defect or a gap.

const {
  AlignmentType, BorderStyle, ImageRun, Paragraph, ShadingType, Table, TableCell,
  TableRow, TextRun, WidthType, HeadingLevel, PageBreak,
} = require('docx');
const fs = require('fs');
const path = require('path');

const INK = '1A2230';
const BODY = '30394A';
const MUTED = '6B7686';
const ACCENT = '1F4E79';
const GREEN = '2E7D52';
const AMBER = '9A6510';
const RED = 'A8332C';
const TINT = 'F2F5F9';
const TINT_WARM = 'FDF6E8';
const TINT_GREEN = 'EFF6F1';
const TINT_RED = 'FBF0EF';
const RULE = 'D6DDE6';

const HEAD_FONT = 'Cambria';
const TEXT_FONT = 'Calibri';

// A4 (11906 dxa) less 2 x 1080 dxa margins.
const CONTENT_W = 9746;

// ---------------------------------------------------------------- text ----

// Turn "plain text with **bold** and _italic_ and `code`" into runs.
// Keeps the content files readable; nothing here is markdown beyond these three.
function runs(text, opts = {}) {
  const size = opts.size || 21;            // half-points: 21 = 10.5 pt
  const color = opts.color || BODY;
  const font = opts.font || TEXT_FONT;
  const out = [];
  const re = /(\*\*[^*]+\*\*|_[^_]+_|`[^`]+`)/g;
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      out.push(new TextRun({ text: text.slice(last, m.index), size, color, font }));
    }
    const tok = m[0];
    if (tok.startsWith('**')) {
      out.push(new TextRun({ text: tok.slice(2, -2), size, color: opts.boldColor || INK, font, bold: true }));
    } else if (tok.startsWith('_')) {
      out.push(new TextRun({ text: tok.slice(1, -1), size, color, font, italics: true }));
    } else {
      out.push(new TextRun({ text: tok.slice(1, -1), size: size - 1, color: ACCENT, font: 'Consolas' }));
    }
    last = m.index + tok.length;
  }
  if (last < text.length) {
    out.push(new TextRun({ text: text.slice(last), size, color, font }));
  }
  return out;
}

// ---------------------------------------------------------- paragraphs ----

function p(text, opts = {}) {
  return new Paragraph({
    children: runs(text, opts),
    spacing: { before: opts.before === undefined ? 60 : opts.before,
               after: opts.after === undefined ? 120 : opts.after,
               line: 268 },
    alignment: opts.align,
    indent: opts.indent,
  });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    pageBreakBefore: true,
    spacing: { before: 0, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: ACCENT, space: 8 } },
    children: [new TextRun({ text, font: HEAD_FONT, size: 34, bold: true, color: INK })],
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 320, after: 120 },
    children: [new TextRun({ text, font: HEAD_FONT, size: 26, bold: true, color: ACCENT })],
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 240, after: 90 },
    children: [new TextRun({ text, font: HEAD_FONT, size: 22, bold: true, color: INK })],
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    children: runs(text),
    numbering: { reference: 'bullets', level },
    spacing: { before: 40, after: 60, line: 264 },
  });
}

function num(text, level = 0) {
  return new Paragraph({
    children: runs(text),
    numbering: { reference: 'numbers', level },
    spacing: { before: 40, after: 60, line: 264 },
  });
}

// A boxed aside. `kind` picks the colour: analogy (blue), good (green),
// warn (amber), bad (red).
const BOX = {
  analogy: { fill: TINT, bar: ACCENT, label: 'THE ANALOGY' },
  note: { fill: TINT, bar: ACCENT, label: null },
  good: { fill: TINT_GREEN, bar: GREEN, label: null },
  warn: { fill: TINT_WARM, bar: AMBER, label: null },
  bad: { fill: TINT_RED, bar: RED, label: null },
};

function box(kind, label, lines) {
  const cfg = BOX[kind] || BOX.note;
  const body = [];
  const heading = label === null ? cfg.label : label;
  if (heading) {
    body.push(new Paragraph({
      spacing: { before: 40, after: 70 },
      children: [new TextRun({
        text: heading.toUpperCase(), font: TEXT_FONT, size: 16, bold: true,
        color: cfg.bar, characterSpacing: 24,
      })],
    }));
  }
  (Array.isArray(lines) ? lines : [lines]).forEach((line, i) => {
    body.push(new Paragraph({
      spacing: { before: i === 0 ? 0 : 80, after: 40, line: 268 },
      children: runs(line, { size: 20 }),
    }));
  });
  return new Table({
    columnWidths: [CONTENT_W],
    width: { size: CONTENT_W, type: WidthType.DXA },
    borders: {
      top: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      bottom: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      right: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      left: { style: BorderStyle.SINGLE, size: 18, color: cfg.bar },
      insideHorizontal: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      insideVertical: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
    },
    rows: [new TableRow({
      children: [new TableCell({
        width: { size: CONTENT_W, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: cfg.fill, color: 'auto' },
        margins: { top: 140, bottom: 140, left: 200, right: 200 },
        children: body,
      })],
    })],
  });
}

const analogy = (lines) => box('analogy', undefined, lines);
const note = (label, lines) => box('note', label, lines);
const good = (label, lines) => box('good', label, lines);
const warn = (label, lines) => box('warn', label, lines);
const bad = (label, lines) => box('bad', label, lines);

// Spacer so a box is not glued to the paragraph under it.
const gap = (h = 120) => new Paragraph({ spacing: { before: 0, after: h }, children: [] });

// ------------------------------------------------------------- tables ----

function table(headers, rows, weights) {
  const n = headers.length;
  const w = weights || new Array(n).fill(1 / n);
  const widths = w.map((x) => Math.round(x * CONTENT_W));
  // make the widths sum exactly
  widths[n - 1] += CONTENT_W - widths.reduce((a, b) => a + b, 0);

  const cell = (text, i, isHead) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    shading: isHead
      ? { type: ShadingType.CLEAR, fill: ACCENT, color: 'auto' }
      : { type: ShadingType.CLEAR, fill: 'FFFFFF', color: 'auto' },
    margins: { top: 80, bottom: 80, left: 110, right: 110 },
    children: [new Paragraph({
      spacing: { before: 0, after: 0, line: 252 },
      children: runs(String(text), {
        size: 19,
        color: isHead ? 'FFFFFF' : BODY,
        boldColor: isHead ? 'FFFFFF' : INK,
      }).map((r) => r),
    })],
  });

  const hasHead = headers.some((t) => String(t).trim() !== '');

  const headRow = new TableRow({
    tableHeader: true,
    children: headers.map((t, i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: ACCENT, color: 'auto' },
      margins: { top: 90, bottom: 90, left: 110, right: 110 },
      children: [new Paragraph({
        spacing: { before: 0, after: 0 },
        children: [new TextRun({ text: String(t), font: TEXT_FONT, size: 19, bold: true, color: 'FFFFFF' })],
      })],
    })),
  });

  const bodyRows = rows.map((r, ri) => new TableRow({
    children: r.map((t, i) => {
      const c = cell(t, i, false);
      if (ri % 2 === 1) {
        c.root.find; // no-op; shading set below via options is not mutable, so rebuild
      }
      return c;
    }),
  }));

  return new Table({
    columnWidths: widths,
    width: { size: CONTENT_W, type: WidthType.DXA },
    borders: {
      top: { style: BorderStyle.SINGLE, size: hasHead ? 4 : 8, color: hasHead ? RULE : ACCENT },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE },
      left: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      right: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      insideVertical: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
    },
    rows: hasHead ? [headRow, ...bodyRows] : bodyRows,
  });
}

// -------------------------------------------------------------- image ----

const FIG_DIR = path.join(__dirname, '..', '..', 'aps_report', 'seminar_final', 'assets', 'slide');
const MAX_W = 640;      // px at 96 dpi; the 9746 dxa text column is 6.77 in
const MAX_H = 440;

// Drop in one of the report's own figures, scaled to fit the column.
// `name` is the file stem in assets/slide, e.g. 'fig09'.
function figure(name, caption) {
  const file = path.join(FIG_DIR, name + '.png');
  if (!fs.existsSync(file)) {
    return [p('[figure ' + name + ' not found: run assets/crop_figs.py]', { color: RED })];
  }
  const { width, height } = pngSize(file);
  const scale = Math.min(MAX_W / width, MAX_H / height, 1);
  const out = [new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 160, after: caption ? 60 : 160 },
    children: [new ImageRun({
      type: 'png',
      data: fs.readFileSync(file),
      transformation: { width: Math.round(width * scale), height: Math.round(height * scale) },
    })],
  })];
  if (caption) {
    out.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 200 },
      children: [new TextRun({ text: caption, font: TEXT_FONT, size: 17, italics: true, color: MUTED })],
    }));
  }
  return out;
}

// Read width and height out of a PNG header. Avoids pulling in an image library
// for two integers.
function pngSize(file) {
  const fd = fs.openSync(file, 'r');
  const buf = Buffer.alloc(24);
  fs.readSync(fd, buf, 0, 24, 0);
  fs.closeSync(fd);
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

// ------------------------------------------------------------ formula ----

// A display equation. Plain text, centred, in the code face so the symbols
// line up. docx-js has no equation editor and OMML by hand is not worth it
// for a study document.
function eq(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 160, after: 160 },
    children: [new TextRun({ text, font: 'Consolas', size: 21, color: INK })],
  });
}

// A block of code or a literal config extract.
function code(lines) {
  const body = (Array.isArray(lines) ? lines : [lines]).map((l, i) => new Paragraph({
    spacing: { before: i === 0 ? 0 : 0, after: 0, line: 240 },
    children: [new TextRun({ text: l, font: 'Consolas', size: 18, color: INK })],
  }));
  return new Table({
    columnWidths: [CONTENT_W],
    width: { size: CONTENT_W, type: WidthType.DXA },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: RULE },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE },
      left: { style: BorderStyle.SINGLE, size: 4, color: RULE },
      right: { style: BorderStyle.SINGLE, size: 4, color: RULE },
      insideHorizontal: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      insideVertical: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
    },
    rows: [new TableRow({
      children: [new TableCell({
        width: { size: CONTENT_W, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: 'F7F8FA', color: 'auto' },
        margins: { top: 130, bottom: 130, left: 180, right: 180 },
        children: body,
      })],
    })],
  });
}

// ------------------------------------------------------------ Q and A ----

function qa(question, answerLines) {
  const out = [new Paragraph({
    spacing: { before: 240, after: 80 },
    keepNext: true,
    children: [
      new TextRun({ text: 'Q.  ', font: HEAD_FONT, size: 21, bold: true, color: ACCENT }),
      new TextRun({ text: question, font: HEAD_FONT, size: 21, bold: true, color: INK }),
    ],
  })];
  (Array.isArray(answerLines) ? answerLines : [answerLines]).forEach((a, i) => {
    out.push(new Paragraph({
      spacing: { before: i === 0 ? 0 : 90, after: 60, line: 268 },
      indent: { left: 340 },
      children: runs(a, { size: 20 }),
    }));
  });
  return out;
}

const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

module.exports = {
  INK, BODY, MUTED, ACCENT, GREEN, AMBER, RED, TINT, RULE,
  HEAD_FONT, TEXT_FONT, CONTENT_W,
  runs, p, h1, h2, h3, bullet, num, box, analogy, note, good, warn, bad,
  gap, table, eq, code, qa, pageBreak, figure,
};
