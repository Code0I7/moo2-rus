# -*- coding: utf-8 -*-
"""Print entries of one extracted text file: id <TAB> cap <TAB> english."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT

name = sys.argv[1].upper().replace('.LBX', '').replace('.JSON', '')
start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
count = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9
d = json.load(open(os.path.join(PROJ, 'text', name + '.json'), encoding='utf-8'))
ent = d['entries'][start:start + count]
print('# %s  mode=%s  %d/%d entries' % (d['file'], d['mode'], len(ent), len(d['entries'])))
for e in ent:
    flag = 'R' if e.get('ru') else '-'
    print('%s\t%s\t%d\t%s' % (flag, e['id'], e['cap'], json.dumps(e['en'], ensure_ascii=False)))
