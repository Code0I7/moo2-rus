# -*- coding: utf-8 -*-
"""Merge tr/*.jsonl translation files into text/*.json.

tr/<FILE>.jsonl   - one ["<entry id>", "<russian>"] per line
tr/_global.jsonl  - one ["<english>", "<russian>"] per line, applied to
                        every entry of every file whose english text matches
"""
import sys, os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
TR = os.path.join(PROJ, 'tr')
TEXT = os.path.join(PROJ, 'text')


def load_jsonl(path):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8') as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            try:
                # strict=False: a translation may carry a raw  column code
                k, v = json.loads(line, strict=False)
            except Exception as e:
                raise SystemExit('%s:%d  %s' % (path, ln, e))
            out[k] = v
    return out


# files where one sub-file per language holds the same list; translating the
# English one and copying it over the others makes the build language agnostic
FANOUT = {'TECHNAME.LBX': 6}
# files where the sub-files come in groups of one per language
# (0 = English, 1 = German, 2 = French, 3 = Spanish, 4 = Italian, 5 = English);
# the English entry is translated and copied across its whole group
GROUP_FANOUT = {'KENTEXT.LBX': 6, 'KENTEXT1.LBX': 6, 'JIMTEXT.LBX': 6,
                'JIMTEXT2.LBX': 6, 'BILLTEXT.LBX': 6, 'BILLTEX2.LBX': 6}
# files that hold one whole message list per language, back to back; entry i
# of the first (English) block is copied to i + B, i + 2B, ... so the game
# shows Russian whatever language block it picks from
BLOCK_FANOUT = {'COUNCMSG.LBX': 14, 'ANTARMSG.LBX': 8}
# files where each language is its own sub-file: translate the English one and
# copy it over the rest, per group of sub-files
SUB_FANOUT = {
    'RACESTUF.LBX': {'0': list('12345'), '8': ['9', '10', '11', '12', '13']},
    'CUSTMSTR.LBX': {'0': ['1', '2']},
}


def norm(s):
    """whitespace-insensitive key, for matching the same sentence across files"""
    return ' '.join(s.split())


def reusable(s):
    """May this English text pick up a translation made for another file?

    Only real words qualify.  One- and two-letter records are hot keys ('B -
    Add bc's to treasury' is followed by a bare 'B'), leftovers behind the NUL
    of a fixed-size name field (STARNAME 'Uz', NUL, 'ith', HERODATA) or data bytes in
    the HELP tech lists; matching them against the ship design arc 'B' = 'З'
    silently rewrote all of those.
    """
    return sum(ch.isalpha() for ch in s) >= 3


def main():
    gl = load_jsonl(os.path.join(TR, '_global.jsonl'))
    total = 0
    docs = []
    for jf in sorted(glob.glob(os.path.join(TEXT, '*.json'))):
        d = json.load(open(jf, encoding='utf-8'))
        base = d['file'].replace('.LBX', '')
        per = {}
        # machine transliteration first, then the base file, the numbered parts
        # and finally .fix, so anything written by hand wins
        for p in ([os.path.join(TR, base + '.auto.jsonl'),
                   os.path.join(TR, base + '.jsonl')] +
                  sorted(glob.glob(os.path.join(TR, base + '.[0-9]*.jsonl'))) +
                  sorted(glob.glob(os.path.join(TR, base + '.fix.jsonl')))):
            per.update(load_jsonl(p))
        if d['file'] in FANOUT:
            for k, v in list(per.items()):
                it, rest = k.split('/', 1)
                if it == '0':
                    for other in range(1, FANOUT[d['file']]):
                        per.setdefault('%d/%s' % (other, rest), v)
        if d['file'] in SUB_FANOUT:
            for src, dsts in SUB_FANOUT[d['file']].items():
                for k, v in list(per.items()):
                    it, rest = k.split('/', 1)
                    if it == src:
                        for other in dsts:
                            per.setdefault('%s/%s' % (other, rest), v)
        if d['file'] in BLOCK_FANOUT:
            b = BLOCK_FANOUT[d['file']]
            n = len(d['entries'])
            for k, v in list(per.items()):
                it, rest = k.split('/', 1)
                for other in range(int(it) % b, n, b):
                    per.setdefault('%d/%s' % (other, rest), v)
        if d['file'] in GROUP_FANOUT:
            g = GROUP_FANOUT[d['file']]
            for k, v in list(per.items()):
                it, rest = k.split('/', 1)
                base = (int(it) // g) * g
                for other in range(base, base + g):
                    per.setdefault('%d/%s' % (other, rest), v)
        n = 0
        for e in d['entries']:
            ru = per.get(e['id'])
            if ru is None:
                ru = gl.get(e['en'])
            if ru is not None:
                e['ru'] = ru
                n += 1
            elif 'ru' in e:
                del e['ru']
        if n:
            total += n
        docs.append((jf, d, n))

    # second pass: the same English sentence appears in several LBX files
    # (MSGENG mirrors HESTRNGS, JIMTEXT mirrors KENTEXT, ...) - reuse what has
    # already been translated, ignoring differences in whitespace
    auto = {}
    for _, d, _ in docs:
        for e in d['entries']:
            # a blank key would match every whitespace-only record, including
            # the ones that are really binary data in a picture sub-file
            if e.get('ru') and reusable(e['en']):
                auto.setdefault(norm(e['en']), e['ru'])
    for jf, d, n in docs:
        extra = 0
        for e in d['entries']:
            if e.get('ru') or not reusable(e['en']):
                continue
            ru = auto.get(norm(e['en']))
            if ru:
                e['ru'] = ru
                extra += 1
        if n or extra:
            print('%-14s %5d + %-4d auto / %-5d' % (d['file'], n, extra, len(d['entries'])))
        total += extra
        json.dump(d, open(jf, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('total', total)


if __name__ == '__main__':
    main()
