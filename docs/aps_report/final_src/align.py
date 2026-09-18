"""Find the crop of a high-resolution source that matches an embedded figure.

The figures in the .docx are downsampled, and several were trimmed before being
placed, so a straight swap would change the framing. This searches the source
for the crop box whose content matches the embedded image, so the replacement
shows exactly what the document already shows, only sharper.
"""
from PIL import Image, ImageOps
import sys

N = 48


def sig(im):
    return list(ImageOps.fit(im.convert('L'), (N, N), Image.BILINEAR).get_flattened_data())


def rms(a, b):
    return (sum((x - y) ** 2 for x, y in zip(a, b)) / len(a)) ** 0.5


def find_crop(emb_path, src_path, work=560):
    E = Image.open(emb_path)
    R0 = Image.open(src_path)
    we, he = E.size
    ar = we / he
    sc = work / max(R0.size)
    R = R0.convert('L').resize((max(1, int(R0.size[0] * sc)),
                                max(1, int(R0.size[1] * sc))), Image.BILINEAR)
    W, H = R.size
    e = sig(E)
    best = None

    def score(fw, fx, fy):
        cw = fw * W
        ch = cw / ar
        if cw < 30 or ch < 30 or cw > W or ch > H:
            return None
        x0 = fx * (W - cw)
        y0 = fy * (H - ch)
        box = (int(round(x0)), int(round(y0)), int(round(x0 + cw)), int(round(y0 + ch)))
        if box[0] < 0 or box[1] < 0 or box[2] > W or box[3] > H:
            return None
        return rms(e, sig(R.crop(box))), (fw, fx, fy), box

    for fw in [i / 32 for i in range(12, 33)]:
        for fx in [i / 10 for i in range(11)]:
            for fy in [i / 10 for i in range(11)]:
                s = score(fw, fx, fy)
                if s and (best is None or s[0] < best[0]):
                    best = s
    for step in (1 / 40, 1 / 160, 1 / 640):
        fw0, fx0, fy0 = best[1]
        for dw in [k * step for k in range(-4, 5)]:
            for dx in [k * step for k in range(-4, 5)]:
                for dy in [k * step for k in range(-4, 5)]:
                    s = score(fw0 + dw, fx0 + dx, fy0 + dy)
                    if s and s[0] < best[0]:
                        best = s
    r, _, box = best
    inv = 1 / sc
    full = (max(0, int(round(box[0] * inv))), max(0, int(round(box[1] * inv))),
            min(R0.size[0], int(round(box[2] * inv))), min(R0.size[1], int(round(box[3] * inv))))
    return r, full


if __name__ == '__main__':
    r, box = find_crop(sys.argv[1], sys.argv[2])
    print('%-12s <- %-44s rms=%6.2f crop=%s -> %dx%d' % (
        sys.argv[1].split('/')[-1], sys.argv[2].split('/')[-1], r, box,
        box[2] - box[0], box[3] - box[1]))
