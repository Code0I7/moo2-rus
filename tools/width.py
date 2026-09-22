# -*- coding: utf-8 -*-
"""Measure rendered pixel width of game strings and flag Russian text that is
wider than the English it replaces.

The engine advances the pen by widths[ch] + spacing[font] per character
(Print_Character_ at 0x111de1, spacing table at FONTS.LBX file offset 0x57C),
so a string fits wherever the English one fitted as long as it is no wider.
Only short single-line labels matter: longer texts are word wrapped.
"""
import sys, os, json, glob, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
from lbx import Lbx
from moo2font import FontFile

SPACING = [1, 1, 2, 2, 2, 3]
CTRL = set(range(0x00, 0x20)) | set(range(0x80, 0x96)) | {0x9E}


def load_fonts(path=None):
    p = path or os.path.join(ROOT, '150', 'mods', 'rus', 'lbx', 'FONTS.LBX')
    return FontFile(Lbx.load(p).items[0])


def enc(s):
    out = bytearray()
    for ch in s:
        o = ord(ch)
        out.append(o) if o < 0x100 else out.extend(ch.encode('cp1251'))
    return bytes(out)


def width(F, fi, s):
    f = F.fonts[fi]
    w = 0
    for b in enc(s):
        if b in CTRL:
            continue
        w += f.widths[b] + SPACING[fi]
    return w


def scan(max_len=48, ratio=1.0, font=3):
    F = load_fonts()
    rows = []
    for jf in sorted(glob.glob(os.path.join(PROJ, 'text', '*.json'))):
        d = json.load(open(jf, encoding='utf-8'))
        seen = set()
        for e in d['entries']:
            ru = e.get('ru')
            if not ru or len(e['en']) > max_len or '\n' in e['en']:
                continue
            if (e['en'], ru) in seen:
                continue
            seen.add((e['en'], ru))
            we, wr = width(F, font, e['en']), width(F, font, ru)
            if we and wr > we * ratio:
                rows.append((wr - we, d['file'], e['id'], e['en'], ru, we, wr))
    rows.sort(key=lambda r: -r[0])
    return rows


if __name__ == '__main__':
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    rows = scan()
    print('# %d labels wider than their English source (font 3, px)' % len(rows))
    for dw, f, i, en, ru, we, wr in rows[:lim]:
        print('%+4d  %-14s %-12s %3d->%3d  %-42s %s' % (dw, f, i, we, wr, en, ru))
