# -*- coding: utf-8 -*-
"""Rewrite translations in place.

    python settr.py <FILE> <patch.jsonl>

<patch.jsonl> holds ["<entry id>", "<russian>"] lines.  Each one replaces the
line of tr/<FILE>*.jsonl that currently wins for that id (the same order
apply_tr.py reads them in), so every id keeps exactly one live translation
instead of piling up overrides.  Ids nobody translated yet are appended to
tr/<FILE>.jsonl.
"""
import sys, os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
from apply_tr import load_jsonl
TR = os.path.join(PROJ, 'tr')


def order(base):
    return ([os.path.join(TR, base + '.auto.jsonl'), os.path.join(TR, base + '.jsonl')] +
            sorted(glob.glob(os.path.join(TR, base + '.[0-9]*.jsonl'))) +
            sorted(glob.glob(os.path.join(TR, base + '.fix.jsonl'))))


def line_for(k, v):
    return json.dumps([k, v], ensure_ascii=False) + '\n'


def main(base, patch):
    new = load_jsonl(patch)
    owner = {}
    for p in order(base):
        for k in load_jsonl(p):
            owner[k] = p
    by_file = {}
    for k, v in new.items():
        by_file.setdefault(owner.get(k, os.path.join(TR, base + '.jsonl')), {})[k] = v
    for p, kv in by_file.items():
        lines = open(p, encoding='utf-8').read().splitlines(True) if os.path.exists(p) else []
        done = set()
        for i, line in enumerate(lines):
            s = line.strip()
            if not s or s.startswith('//'):
                continue
            k = json.loads(s, strict=False)[0]
            if k in kv:
                lines[i] = line_for(k, kv[k])
                done.add(k)
        for k, v in kv.items():
            if k not in done:
                if lines and not lines[-1].endswith('\n'):
                    lines[-1] += '\n'
                lines.append(line_for(k, v))
        open(p, 'w', encoding='utf-8').writelines(lines)
        print('%-28s %3d replaced %3d added' % (os.path.basename(p), len(done), len(kv) - len(done)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
