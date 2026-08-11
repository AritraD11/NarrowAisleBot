# Robot Photos

Dated photographic record of the physical robot — mount positions, test setups,
and hardware states — kept alongside the written record so a claim in
`Research_Journal.md` can be checked against what the robot actually looked like
at the time.

## Convention

One folder per session or trial, named `YYYY-MM-DD_short_description/`.

Each image is stored twice:

- **`.heic`** — the original straight off the phone, untouched.
- **`.jpg`** — a downscaled (1600 px long edge) copy. This exists because
  **GitHub cannot preview HEIC in the browser**; the JPEG is what actually
  renders in a pull request, in a Markdown embed, or when someone clicks the
  file. Generate it with `pillow-heif`, do not hand-convert.

Filenames are lowercase, ASCII, underscore-separated. Avoid spaces and the
degree symbol (`°`) — the original upload used `CW 90°.HEIC`, which needs shell
escaping (`CW 90\302\260.HEIC`) every time it is referenced from a script, and
one file carried a trailing space before its extension that is effectively
invisible in a listing. Write `cw_090` and the problem disappears.

Every folder gets a `README.md` captioning each image: what it shows, and what
question it was taken to answer.

---

## Index

| Folder | Date | What it documents |
|---|---|---|
| [`2026-08-11_occlusion_trial_cw/`](2026-08-11_occlusion_trial_cw/) | 11 Aug 2026 | Robot orientation at each 90° stop of the clockwise self-occlusion trial (Research_Journal.md §17.8) |

Earlier hardware photos — the three LiDAR mount positions from the §17.4
placement trial — were shared in-session and are not yet in this folder. Add
them here if the originals are still to hand; the placement trial's conclusions
depend on them.
