# Deck generator

Builds `../NarrowAisleBot_APS_Seminar.pptx` from this project's own photographs
and generated figures. Nothing is fetched from the network and no stock imagery
is used.

```sh
npm install          # pptxgenjs, once
node build_deck.js   # writes the .pptx
python3 preview.py   # renders preview/slide-NN.png and reports any overflow
```

`build_deck.js` holds the slide content in one `SLIDES` array — edit the text
there and rebuild rather than editing the `.pptx`, or the two will diverge. The
figure for each slide is named in the same array and read from `../figures/`.

`preview.py` exists because LibreOffice cannot run in the environment this was
authored in, so the usual convert-to-PDF check is unavailable. It reproduces the
same box geometry with PIL and fails loudly on text that would overflow its box,
a figure that would collide with the title, or cards that would touch. It reads
its slide list out of `build_deck.js`, so the two cannot drift apart.

The stand-in fonts matter: Liberation Sans carries Arial's metrics, which are
wider than the Calibri the deck actually asks for, so text that fits in the
preview fits in PowerPoint with room to spare. Liberation Serif is narrower than
Cambria, so titles are checked against a 6 per cent margin instead of the box
edge.
