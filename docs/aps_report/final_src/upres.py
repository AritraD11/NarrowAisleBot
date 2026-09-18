"""Swap every figure in the .docx for the highest-resolution source in the repo.

The document places each picture in a fixed extent box and applies no Word-side
crop, so replacing the media file with a larger one of the same content leaves
the layout untouched and only raises the pixel density. Where the placed image
was trimmed before insertion, the replacement is cropped to the same framing so
the page looks identical.
"""
import os, re, shutil, zipfile
from PIL import Image

REPO = '/home/user/NarrowAisleBot'
SRC = '/tmp/docxwork/src.docx'
WORK = '/tmp/docxwork/out'
OUT = '/home/user/NarrowAisleBot/docs/aps_report/APS report Aritra - high resolution.docx'

F = f'{REPO}/docs/aps_report/figures'

# media -> (source, crop box or None, output extension)
PLAN = {
    'image3.jpg':  (f'{F}/fig24_platform_photos.png',      None, 'jpg'),
    'image4.png':  (f'{REPO}/docs/hardware/nab_circuit_diagram.png', None, 'png'),
    'image5.png':  (f'{F}/fig01_asymmetric_geometry.png',  None, 'png'),
    'image6.png':  (f'{F}/fig26_iot_architecture.png',     None, 'png'),
    'image8.png':  (f'{F}/fig05_feedforward_model.png',    None, 'png'),
    'image9.png':  (f'{F}/fig08_v30_tracking.png',         None, 'png'),
    'image10.png': (f'{F}/fig10_ground_load.png',          None, 'png'),
    'image12.jpg': (f'{F}/fig12_self_occlusion.png',       None, 'png'),
    'image13.png': (f'{F}/fig17_rotation_deadzone.png',    None, 'png'),
    'image14.png': (f'{F}/fig29_field_maps.png',           None, 'png'),
    'image15.jpg': (f'{F}/fig22_layer_audit.png', (0, 425, 3798, 3289), 'png'),
}
# left as they are: image1 (institute crest), image2 (Figure 1 platform
# photograph) and image7 (Figure 6, the air-treatment unit) have no
# higher-resolution original anywhere in the repository.
KEEP = {'image1.png', 'image2.jpg', 'image7.jpg'}

# Figure 10 has no source in the repository, and this copy still carries the
# stale "three autonomous drives" title that the submitted version cropped off.
# The title band is rows 0 to 24; removing it and padding the same number of
# rows at the foot keeps the picture's proportions, so the extent box in the
# document still fits it exactly and nothing is stretched.
def fix_figure10(path):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    out = Image.new('RGB', (w, h), 'white')
    out.paste(im.crop((0, 25, w, h)), (0, 0))
    out.save(path, 'PNG', optimize=True)
    return (w, h)


def build():
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    with zipfile.ZipFile(SRC) as z:
        names = z.namelist()
        z.extractall(WORK)

    renames = {}
    report = []
    for media, (src, crop, ext) in PLAN.items():
        old = f'{WORK}/word/media/{media}'
        before = Image.open(old).size
        im = Image.open(src)
        if crop:
            im = im.crop(crop)
        stem = media.rsplit('.', 1)[0]
        new_name = f'{stem}.{ext}'
        new_path = f'{WORK}/word/media/{new_name}'
        if ext == 'jpg':
            im.convert('RGB').save(new_path, 'JPEG', quality=94, subsampling=0,
                                   optimize=True)
        else:
            im.convert('RGB').save(new_path, 'PNG', optimize=True)
        if new_name != media:
            os.remove(old)
            renames[media] = new_name
        report.append((media, new_name, before, im.size, os.path.getsize(new_path)))

    fix_figure10(f'{WORK}/word/media/image11.png')

    if renames:
        rp = f'{WORK}/word/_rels/document.xml.rels'
        x = open(rp, encoding='utf-8').read()
        for a, b in renames.items():
            x = x.replace(f'Target="media/{a}"', f'Target="media/{b}"')
        open(rp, 'w', encoding='utf-8').write(x)

    # repack, keeping the original entry order
    if os.path.exists(OUT):
        os.remove(OUT)
    with zipfile.ZipFile(SRC) as z0, zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
        written = set()
        for n in z0.namelist():
            base = os.path.basename(n)
            target = n
            if base in renames:
                target = n.replace(base, renames[base])
            p = f'{WORK}/{target}'
            if not os.path.exists(p):
                continue
            z.write(p, target)
            written.add(target)
        for root, _, files in os.walk(WORK):
            for fn in files:
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, WORK).replace(os.sep, '/')
                if rel not in written:
                    z.write(p, rel)
    return report


if __name__ == '__main__':
    rows = build()
    print('%-13s -> %-13s %-12s %-12s %s' % ('was', 'now', 'old px', 'new px', 'KB'))
    for a, b, o, n, s in rows:
        print('%-13s -> %-13s %-12s %-12s %d' % (a, b, '%dx%d' % o, '%dx%d' % n, s // 1024))
    print('\nleft unchanged (no higher-resolution source in the repo):',
          ', '.join(sorted(KEEP)))
    print('wrote', OUT, '%.1f MB' % (os.path.getsize(OUT) / 1e6))
