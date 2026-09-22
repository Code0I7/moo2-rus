# -*- coding: utf-8 -*-
"""Render a PNG sheet of the generated Cyrillic alphabet for every font."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
from lbx import Lbx
from moo2font import FontFile
from PIL import Image

PAL = {None: (25, 25, 35), 0: (0, 0, 0), 1: (110, 110, 130), 2: (230, 230, 235),
       3: (255, 255, 255), 4: (255, 220, 160), 5: (255, 170, 80), 6: (200, 120, 50),
       7: (150, 90, 40), 8: (255, 255, 200)}


def render_text(f, text, scale):
    codes = [c.encode('cp1251')[0] for c in text]
    W = sum(max(f.widths[c], 1) + 1 for c in codes) + 2
    H = f.height + 2
    img = Image.new('RGB', (W, H), (25, 25, 35))
    x = 1
    for c in codes:
        g = f.glyphs[c]
        if g:
            for y, row in enumerate(g):
                for i, p in enumerate(row):
                    if p is not None and 0 <= x + i < W:
                        img.putpixel((x + i, y + 1), PAL.get(p, (255, 0, 255)))
        x += max(f.widths[c], 1) + 1
    return img.resize((W * scale, H * scale), Image.NEAREST)


def main(path, out, scale_by_font=(8, 7, 6, 5, 4, 3)):
    L = Lbx.load(path)
    F = FontFile(L.items[0])
    lines = ['АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ',
             'абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
             'Колония Исследования Корабли Флот',
             'Производство Население Разведка 123']
    imgs = []
    for fi, f in enumerate(F.fonts):
        for ln in lines:
            imgs.append(render_text(f, ln, scale_by_font[fi]))
    TW = max(i.width for i in imgs)
    TH = sum(i.height + 4 for i in imgs)
    sheet = Image.new('RGB', (TW, TH), (10, 10, 15))
    y = 0
    for i in imgs:
        sheet.paste(i, (0, y))
        y += i.height + 4
    sheet.save(out)
    print('saved', out, sheet.size)


if __name__ == '__main__':
    root = ROOT
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, '150', 'mods', 'rus', 'lbx', 'FONTS.LBX'),
         sys.argv[2] if len(sys.argv) > 2 else os.path.join(PROJ, 'work', 'cyr_preview.png'))
