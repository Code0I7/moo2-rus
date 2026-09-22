# -*- coding: utf-8 -*-
"""Print only the English entries of a language-grouped LBX (every 6th sub-file)."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT

name = sys.argv[1].upper().replace('.LBX', '')
group = int(sys.argv[2]) if len(sys.argv) > 2 else 6
start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
count = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9
d = json.load(open(os.path.join(PROJ, 'text', name + '.json'), encoding='utf-8'))
sel = [e for e in d['entries'] if int(e['id'].split('/')[0]) % group == 0]
print('# %s  %d english entries (of %d)' % (d['file'], len(sel), len(d['entries'])))
for e in sel[start:start + count]:
    flag = 'R' if e.get('ru') else '-'
    print('%s\t%s\t%d\t%s' % (flag, e['id'], e['cap'], json.dumps(e['en'], ensure_ascii=False)))
