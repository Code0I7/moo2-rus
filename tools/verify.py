# -*- coding: utf-8 -*-
"""Check that every translated string really made it into the built LBX.

build.py reports what it injected, but it cannot notice that it read the wrong
source: install.py replaces a few LBX in the game root, and a rebuild that
picks those up sees its own previous output.  Russian records hold no Latin
letter, so the extractor skips them and the injection silently does nothing.

This looks for the encoded bytes of every translated string inside the file
that was actually produced, which catches that and any truncation.
"""
import os, sys, json, glob

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
OUT = os.path.join(ROOT, '150', 'mods', 'rus', 'lbx')
TEXT = os.path.join(PROJ, 'text')


def enc(s):
    out = bytearray()
    for ch in s:
        o = ord(ch)
        if o < 0x100:
            out.append(o)
        else:
            out += ch.encode('cp1251')
    return bytes(out)


def main():
    total = missing = 0
    for jf in sorted(glob.glob(os.path.join(TEXT, '*.json'))):
        d = json.load(open(jf, encoding='utf-8'))
        built = os.path.join(OUT, d['file'])
        if not os.path.exists(built):
            continue
        raw = open(built, 'rb').read()
        ok, bad, examples = 0, 0, []
        for e in d['entries']:
            ru = e.get('ru')
            if not ru:
                continue
            if enc(ru) in raw:
                ok += 1
            else:
                bad += 1
                if len(examples) < 3:
                    examples.append((e['id'], ru[:50]))
        total += ok
        missing += bad
        line = '%-14s %5d in file' % (d['file'], ok)
        if bad:
            line += '   MISSING %d  e.g. %s' % (bad, examples)
        print(line)
    print('--- %d strings verified, %d missing' % (total, missing))
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
