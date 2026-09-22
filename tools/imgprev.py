# -*- coding: utf-8 -*-
"""Render LBX sub-file images into a labelled contact sheet PNG."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lbx import Lbx
from lbximg import Image, looks_like_image
from PIL import Image as PImage, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
_base = None


def base_palette():
    global _base
    if _base is None:
        _base = Image.parse(Lbx.load(os.path.join(ROOT, 'MAINMENU.LBX')).items[1]).palette
    return _base


def render(im, frame, pal=None):
    pal = (pal or im).rgb_palette(base_palette()) if not isinstance(pal, list) else pal
    p = PImage.new('RGB', (im.w, im.h), (255, 0, 255))
    px = p.load()
    for y in range(im.h):
        row = frame[y]
        for x in range(im.w):
            v = row[x]
            if v is not None:
                px[x, y] = pal[v]
    return p


def sheet(path, idxs, out, scale=2, pal=None, frames=None):
    L = Lbx.load(path if os.path.isabs(path) else os.path.join(ROOT, path))
    tiles = []
    for i in idxs:
        it = L.items[i]
        if not looks_like_image(it):
            continue
        try:
            im = Image.parse(it)
        except Exception as e:
            print('  skip %d: %s' % (i, e)); continue
        for fi, fr in enumerate(im.frames):
            if frames is not None and fi not in frames:
                continue
            tiles.append(('%d.%d' % (i, fi), render(im, fr, pal)))
    if not tiles:
        print('nothing to draw'); return
    W = max(t[1].width for t in tiles) + 70
    H = sum(t[1].height + 6 for t in tiles)
    s = PImage.new('RGB', (W, H), (30, 30, 30))
    d = ImageDraw.Draw(s)
    y = 0
    for name, p in tiles:
        d.text((2, y + 2), name, fill=(220, 220, 90))
        s.paste(p, (66, y)); y += p.height + 6
    s.resize((W * scale, H * scale), PImage.NEAREST).save(out)
    print(out, len(tiles), 'tiles')


if __name__ == '__main__':
    f = sys.argv[1]
    idxs = []
    for tok in sys.argv[2].split(','):
        if '-' in tok:
            a, b = tok.split('-'); idxs += list(range(int(a), int(b) + 1))
        else:
            idxs.append(int(tok))
    sheet(f, idxs, sys.argv[3] if len(sys.argv) > 3 else os.path.join(PROJ, 'work', 'out.png'))
