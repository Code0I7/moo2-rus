# -*- coding: utf-8 -*-
"""Dump every translatable LBX into text/*.json"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
import lbxtext

FILES = ['HELP.LBX', 'DIPLOMSE.LBX', 'MSGENG.LBX', 'ESTRINGS.LBX', 'HESTRNGS.LBX',
         'JIMTEXT.LBX', 'JIMTEXT2.LBX', 'KENTEXT.LBX', 'KENTEXT1.LBX', 'EVENTMSE.LBX',
         'BILLTEXT.LBX', 'BILLTEX2.LBX', 'SHIPNAME.LBX', 'COUNCMSG.LBX', 'STARNAME.LBX',
         'RSTRING0.LBX', 'ANTARMSG.LBX', 'TECHDESC.LBX', 'SKILDESC.LBX', 'ENGMSG.LBX',
         'MAINTEXT.LBX', 'HERODATA.LBX', 'CREDITS.LBX', 'RACENAME.LBX',
         'TECHNAME.LBX', 'RACESTUF.LBX', 'PLAYSPEC.LBX', 'CUSTMSTR.LBX']
# deliberately skipped: RACEICON/PLNTSUM/COLONY2/FIREPTS/NDATA hold picture data
# that only looks like ASCII, FILEDATA holds sound driver file names.


# The translation targets the "1.50 improved" core mod, which ships its own
# English HELP/TECHDESC/HERODATA/KENTEXT with the numbers it changed (and with
# the stale race pick costs removed), so its copies win over the plain 1.50
# ones.
IMPROVED = os.path.join(ROOT, '150', 'mods', '150i', 'lbx')


# install.py overwrites a dozen LBX in the game root with the Russian build and
# keeps the originals here; dumping the installed copy would read our own
# output back (and skip every record that no longer has a Latin letter)
BACKUP = os.path.join(PROJ, 'backup', 'root')


def source_for(f):
    for cand in [os.path.join(BACKUP, f),
                 os.path.join(IMPROVED, 'en', f),
                 os.path.join(IMPROVED, f),
                 os.path.join(ROOT, '150', 'lbx', 'en', f),
                 os.path.join(ROOT, '150', 'lbx', f),
                 os.path.join(ROOT, f)]:
        if os.path.exists(cand):
            return cand
    return None


def main():
    out = os.path.join(PROJ, 'text')
    os.makedirs(out, exist_ok=True)
    total = 0
    for f in FILES:
        src = source_for(f)
        if not src:
            print('%-14s MISSING' % f)
            continue
        try:
            mode, ent = lbxtext.extract(src)
        except Exception as e:
            print('%-14s ERR %s' % (f, e))
            continue
        if not ent:
            print('%-14s (no text)' % f)
            continue
        ch = sum(len(e['en']) for e in ent)
        total += ch
        with open(os.path.join(out, f.replace('.LBX', '') + '.json'), 'w', encoding='utf-8') as fh:
            json.dump({'file': f, 'src': os.path.relpath(src, ROOT).replace('\\', '/'),
                       'mode': mode, 'entries': ent}, fh, ensure_ascii=False, indent=0)
        print('%-14s %-8s %5d entries %7d chars  src=%s' % (f, mode, len(ent), ch,
                                                            os.path.relpath(src, ROOT)))
    print('TOTAL chars', total)


if __name__ == '__main__':
    main()
