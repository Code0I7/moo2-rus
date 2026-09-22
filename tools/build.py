# -*- coding: utf-8 -*-
"""Build the Russian LBX files from text/*.json into 150/mods/rus/lbx/."""
import sys, os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
import lbxtext

OUT = os.path.join(ROOT, '150', 'mods', 'rus', 'lbx')
# install.py replaces a handful of LBX in the game root, so for those the
# recorded source is by now our own Russian output.  The pristine copy it put
# aside first is the real source; without this the build silently reads back
# what it wrote last time and new edits never reach the file.
BACKUP = os.path.join(PROJ, 'backup', 'root')

# how much a pooled record may grow (bytes); 0 keeps the original size
# the 1.50 patch validates record sizes, so pooled records must keep theirs
GROW = {}


def enc(s):
    """Unicode -> game bytes: latin1 passes straight through (that keeps the
    engine's 0x01-0x1F and 0x80-0x95 control codes intact), everything else
    goes through cp1251."""
    out = bytearray()
    for ch in s:
        o = ord(ch)
        if o < 0x100:
            out.append(o)
        else:
            out += ch.encode('cp1251')
    return bytes(out)


def main(only=None):
    os.makedirs(OUT, exist_ok=True)
    grand = {'files': 0, 'strings': 0, 'trunc': 0}
    for jf in sorted(glob.glob(os.path.join(PROJ, 'text', '*.json'))):
        d = json.load(open(jf, encoding='utf-8'))
        if only and d['file'] not in only:
            continue
        trans = {}
        n = 0
        for e in d['entries']:
            ru = e.get('ru')
            if ru is None or ru == '':
                trans[e['id']] = e['en']
            else:
                trans[e['id']] = enc(ru).decode('latin1')
                n += 1
        if n == 0:
            continue
        src = os.path.join(BACKUP, d['file'])
        if not os.path.exists(src):
            src = os.path.join(ROOT, d['src'])
        dst = os.path.join(OUT, d['file'])
        st = lbxtext.inject(src, d['mode'], trans, dst, grow=GROW.get(d['file'], 0))
        grand['files'] += 1
        grand['strings'] += n
        grand['trunc'] += st['trunc']
        msg = '%-14s %5d translated' % (d['file'], n)
        if st['overflow']:
            msg += '   OVERFLOW x%d  e.g. %s' % (len(st['overflow']), st['overflow'][:3])
        print(msg)
    print('--- %d files, %d strings, %d truncated' % (grand['files'], grand['strings'],
                                                      grand['trunc']))
    import markers
    lost = markers.scan()
    if lost:
        print('--- WARNING: %d strings lost a substitution marker, run markers.py'
              % sum(len(v) for v in lost.values()))


if __name__ == '__main__':
    main(set(sys.argv[1:]) or None)
