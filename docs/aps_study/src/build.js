#!/usr/bin/env node
// Build the APS study guide.
//
//     node docs/aps_study/src/build.js
//
// The .docx is a build artefact. Edit the c*.js content files and rebuild
// rather than editing the Word file, or the two diverge and the generator
// becomes the stale copy.

const fs = require('fs');
const path = require('path');
const {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, LevelFormat,
  PageBreak, PageNumber, Packer, Paragraph, TableOfContents, TextRun,
} = require('docx');

const S = require('./style');

const OUT = path.join(__dirname, '..', 'NarrowAisleBot_APS_Study_Guide.docx');

const PARTS = [
  './c00_front',
  './c01_problem',
  './c02_hardware',
  './c03_kinematics',
  './c04_control',
  './c05_gains',
  './c06_odometry',
  './c08_slam',
  './c09_nav',
  './c10_figures',
  './c11_strands',
  './c12_questions',
  './c13_cheat',
];

// ------------------------------------------------------------- cover ----

function cover() {
  const line = (text, opts) => new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { before: opts.before || 0, after: opts.after || 0 },
    children: [new TextRun({
      text,
      font: opts.font || S.TEXT_FONT,
      size: opts.size || 22,
      bold: opts.bold,
      color: opts.color || S.BODY,
      characterSpacing: opts.spacing,
    })],
  });

  return [
    new Paragraph({ spacing: { before: 1600, after: 0 }, children: [] }),
    line('STUDY GUIDE FOR THE ANNUAL PROGRESS SEMINAR', {
      size: 19, bold: true, color: S.ACCENT, spacing: 48, after: 260,
    }),
    new Paragraph({
      spacing: { before: 0, after: 200 },
      children: [new TextRun({
        text: 'Development and Validation of Narrow-Aisle Robotic and IoT-Based Systems for Warehouse Management',
        font: S.HEAD_FONT, size: 46, bold: true, color: S.INK,
      })],
    }),
    new Paragraph({
      spacing: { before: 0, after: 420 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 16, color: S.ACCENT, space: 10 } },
      children: [],
    }),
    line('Everything in the report, explained in plain language, with the numbers, the reasoning, and the answers to the questions the panel will ask.',
      { size: 24, font: S.HEAD_FONT, color: S.BODY, after: 520 }),
    line('Aritra Das', { size: 26, font: S.HEAD_FONT, bold: true, color: S.INK, after: 90 }),
    line('Roll No. 25D0074', { size: 21, color: S.BODY, after: 90 }),
    line('Supervisor: Prof. Ambarish Kunwar', { size: 21, color: S.BODY, after: 90 }),
    line('Department of Biosciences and Bioengineering, IIT Bombay', { size: 21, color: S.BODY, after: 90 }),
    line('IITB-FedEx ALFA fellowship', { size: 21, color: S.MUTED, after: 520 }),
    line('Seminar: 23 September 2026, 14:30 to 15:30', { size: 21, bold: true, color: S.ACCENT, after: 140 }),
    line('Built against the submitted APS report. Every number in this document traces to that report or to this project\'s own repository.',
      { size: 18, color: S.MUTED }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

function contents() {
  return [
    new Paragraph({
      spacing: { before: 0, after: 240 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: S.ACCENT, space: 8 } },
      children: [new TextRun({ text: 'Contents', font: S.HEAD_FONT, size: 34, bold: true, color: S.INK })],
    }),
    new Paragraph({
      spacing: { before: 0, after: 200 },
      children: [new TextRun({
        text: 'Right-click and choose "Update field" in Word to fill in the page numbers.',
        font: S.TEXT_FONT, size: 18, italics: true, color: S.MUTED,
      })],
    }),
    new TableOfContents('Contents', { hyperlink: true, headingStyleRange: '1-2' }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ------------------------------------------------------------- build ----

function build() {
  const body = [];
  PARTS.forEach((mod) => {
    const chunk = require(mod);
    chunk.forEach((el) => body.push(el));
  });

  const doc = new Document({
    creator: 'Aritra Das',
    title: 'NarrowAisleBot APS Study Guide',
    description: 'Study companion to the first-year Annual Progress Seminar report.',
    numbering: {
      config: [
        {
          reference: 'bullets',
          levels: [
            { level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 360, hanging: 240 } },
                       run: { color: S.ACCENT } } },
            { level: 1, format: LevelFormat.BULLET, text: '◦', alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 720, hanging: 240 } },
                       run: { color: S.ACCENT } } },
          ],
        },
        {
          reference: 'numbers',
          levels: [
            { level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 400, hanging: 280 } },
                       run: { color: S.ACCENT, bold: true } } },
          ],
        },
      ],
    },
    styles: {
      default: {
        document: { run: { font: S.TEXT_FONT, size: 21, color: S.BODY } },
      },
      paragraphStyles: [
        { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { font: S.HEAD_FONT, size: 34, bold: true, color: S.INK } },
        { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { font: S.HEAD_FONT, size: 26, bold: true, color: S.ACCENT } },
        { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { font: S.HEAD_FONT, size: 22, bold: true, color: S.INK } },
      ],
    },
    sections: [{
      properties: {
        page: {
          margin: { top: 1080, right: 1080, bottom: 1080, left: 1080, header: 600, footer: 600 },
        },
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { before: 120, after: 0 },
            children: [
              new TextRun({ text: 'NarrowAisleBot  ·  APS Study Guide  ·  ',
                font: S.TEXT_FONT, size: 16, color: 'A8B1BE' }),
              new TextRun({ children: [PageNumber.CURRENT],
                font: S.HEAD_FONT, size: 17, color: S.MUTED }),
            ],
          })],
        }),
      },
      children: [...cover(), ...contents(), ...body],
    }],
  });

  return Packer.toBuffer(doc).then((buf) => {
    fs.writeFileSync(OUT, buf);
    console.log('wrote %s (%.1f MB)', path.relative(process.cwd(), OUT), buf.length / 1e6);
  });
}

build().catch((e) => { console.error(e); process.exit(1); });
