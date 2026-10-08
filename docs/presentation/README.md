# ROS 2 architecture deck

`NarrowAisleBot_ROS2_Architecture.pdf` is the copy to show: 23 slides, fonts embedded, so it looks the same on an iPad, a laptop or a projector. `NarrowAisleBot_ROS2_Architecture.pptx` is the editable copy. It uses Calibri and Cambria, which PowerPoint has; Keynote on iPad may substitute them, so edit in PowerPoint if the layout matters. Every slide has speaker notes naming where its numbers come from.

## Rebuilding

```
NODE_PATH=<dir containing pptxgenjs> APPLY_THEME=<pptx skill>/scripts/apply_theme.js node docs/presentation/build_deck.js
soffice --headless --convert-to pdf --outdir docs/presentation docs/presentation/NarrowAisleBot_ROS2_Architecture.pptx
```

The figures come from `docs/flowcharts/png/` and `docs/hardware/esp32_pin_circuit.png`; rebuild those first if the system changed (see `docs/flowcharts/README.md`). For a faithful PDF the machine needs Carlito and Caladea (metric-compatible stand-ins for Calibri and Cambria) and LibreOffice Impress.

`img/title_robot.jpg` is cropped from `docs/hardware/photos/nab_full_side_arm_lab_02.jpg`; `img/dims_schematic.png` is cropped from the APS seminar assets.

## Plain Word notes

`NarrowAisleBot_ROS2_Notes.docx` is the same material as plain, black-and-white, editable notes: mostly flowcharts, A4 landscape, Word's own heading styles (all black), no photos. Built by `build_doc.js` from the mono figures:

```
python3 docs/flowcharts/flowcharts.py                         # writes svg/ and mono/svg/
node docs/flowcharts/render_png.js 2 mono                     # mono/png, rendered through a greyscale filter
MONO=1 python3 docs/hardware/esp32_pin_circuit.py && node docs/hardware/render_svg_png.js docs/hardware/esp32_pin_circuit_mono.svg 2
NODE_PATH=<dir containing docx> node docs/presentation/build_doc.js
```

## Final version

`NarrowAisleBot_ROS2_Notes_final.docx` is the author's edited copy (academic register, plus a new section 1 on the Ubuntu and ROS 2 installation), added 8 Oct 2026. It is the version to use. The generated `NarrowAisleBot_ROS2_Notes.docx` is kept as the source it started from; rebuilding it will not reproduce the edits.

Checked against `install.sh` when it was added: section 1 says the `ros-base` variant was installed, while `install.sh` installs `ros-jazzy-desktop`. Confirm on the Pi with `dpkg -l ros-jazzy-desktop ros-jazzy-ros-base`. Section 1 also lists `ros-jazzy-twist-mux`, which the robot runs but `install.sh` does not install.
