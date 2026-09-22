# -*- coding: utf-8 -*-
"""Flag short labels whose Russian text is wider than the English it replaces.

The game renders at 640x480 internally (DOSBox only upscales the finished
frame), and every fixed UI slot was sized for the English string, so
"no wider than English" is a font independent guarantee that it fits.
Long texts are excluded: those go into word wrapped message boxes.

The pen advance is widths[ch] + spacing[font] (Print_Character_ at 0x111de1,
spacing table at FONTS.LBX offset 0x57C), so the ratio between two strings is
almost the same in every font - font 2 is used here as the yardstick.
"""
import sys, os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
from width import load_fonts, width

FONT = 2
# files whose short entries sit in fixed-size slots
TIGHT = {'TECHNAME.LBX': 60, 'HESTRNGS.LBX': 24, 'KENTEXT.LBX': 24, 'KENTEXT1.LBX': 24,
         'ESTRINGS.LBX': 24, 'RSTRING0.LBX': 24, 'TECHDESC.LBX': 44, 'HERODATA.LBX': 30,
         'JIMTEXT.LBX': 30, 'JIMTEXT2.LBX': 24, 'SKILDESC.LBX': 24, 'MSGENG.LBX': 24}


def main(show=200):
    F = load_fonts()
    rows = []
    for jf in sorted(glob.glob(os.path.join(PROJ, 'text', '*.json'))):
        d = json.load(open(jf, encoding='utf-8'))
        lim = TIGHT.get(d['file'])
        if not lim:
            continue
        # only compare against the English source entry: several LBX keep one
        # sub-file per language and the fan-out copies are not a yardstick
        group = 6 if d['file'] in ('TECHNAME.LBX', 'KENTEXT.LBX', 'KENTEXT1.LBX',
                                   'JIMTEXT.LBX', 'JIMTEXT2.LBX') else 1
        seen = set()
        for e in d['entries']:
            it = int(e['id'].split('/')[0])
            if group > 1 and it % group != 0:
                continue
            ru = e.get('ru')
            en = e['en']
            if not ru or ru == en or len(en) > lim or '\n' in en:
                continue
            if (en, ru) in seen:
                continue
            seen.add((en, ru))
            we, wr = width(F, FONT, en), width(F, FONT, ru)
            if wr > we:
                rows.append((wr - we, d['file'], e['id'], en, ru, we, wr))
    rows.sort(key=lambda r: -r[0])
    print('# %d short labels wider than English (font %d, px)' % (len(rows), FONT))
    for dw, f, i, en, ru, we, wr in rows[:show]:
        print('%+4d  %-14s %-10s %3d->%3d  %-34s %s' % (dw, f, i, we, wr, en, ru))
    return rows


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
