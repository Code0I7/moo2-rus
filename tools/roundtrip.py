# -*- coding: utf-8 -*-
"""Re-inject the extracted English text and verify the result is byte identical."""
import sys, os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
import lbxtext

tmp = os.path.join(PROJ, 'work', 'rt')
os.makedirs(tmp, exist_ok=True)
bad = 0
for jf in sorted(glob.glob(os.path.join(PROJ, 'text', '*.json'))):
    d = json.load(open(jf, encoding='utf-8'))
    src = os.path.join(ROOT, d['src'])
    trans = {e['id']: e['en'] for e in d['entries']}
    out = os.path.join(tmp, d['file'])
    st = lbxtext.inject(src, d['mode'], trans, out)
    same = open(src, 'rb').read() == open(out, 'rb').read()
    flag = 'OK ' if same else 'DIFF'
    if not same:
        bad += 1
    print('%s %-14s ok=%d trunc=%d overflow=%d' % (flag, d['file'], st['ok'], st['trunc'],
                                                   len(st['overflow'])))
print('files with differences:', bad)
