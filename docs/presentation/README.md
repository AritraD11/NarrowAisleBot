# ROS 2 architecture deck

`NarrowAisleBot_ROS2_Architecture.pdf` is the copy to show: 23 slides, fonts embedded, so it looks the same on an iPad, a laptop or a projector. `NarrowAisleBot_ROS2_Architecture.pptx` is the editable copy. It uses Calibri and Cambria, which PowerPoint has; Keynote on iPad may substitute them, so edit in PowerPoint if the layout matters. Every slide has speaker notes naming where its numbers come from.

## Rebuilding

```
NODE_PATH=<dir containing pptxgenjs> APPLY_THEME=<pptx skill>/scripts/apply_theme.js node docs/presentation/build_deck.js
soffice --headless --convert-to pdf --outdir docs/presentation docs/presentation/NarrowAisleBot_ROS2_Architecture.pptx
```

The figures come from `docs/flowcharts/png/` and `docs/hardware/esp32_pin_circuit.png`; rebuild those first if the system changed (see `docs/flowcharts/README.md`). For a faithful PDF the machine needs Carlito and Caladea (metric-compatible stand-ins for Calibri and Cambria) and LibreOffice Impress.

`img/title_robot.jpg` is cropped from `docs/hardware/photos/nab_full_side_arm_lab_02.jpg`; `img/dims_schematic.png` is cropped from the APS seminar assets.
