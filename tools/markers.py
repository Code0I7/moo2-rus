# -*- coding: utf-8 -*-
"""Check that translations keep the engine's substitution markers.

Bytes 0x80..0x95 inside a game string are placeholders the engine expands at
print time (ruler name, race, tech, amounts).  They are invisible when the
text is read as prose, so it is easy to translate a line and silently drop
one - the game then prints an empty gap where the name should be.

Run with no arguments for a report; the listing is grouped by the Russian
text, so one fix in tr usually clears a whole group of language copies.
"""
import os, sys, json, glob
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
TEXT = os.path.join(PROJ, 'text')

LOW, HIGH = 0x80, 0x95

# markers a translation is allowed to leave out.   and  expand to a
# race name in the nominative plural, which cannot be bent into the oblique
# cases Russian needs ("of the Klackon Empire"); the diplomacy lines say
# "our"/"your empire" instead, which reads better and loses no information
# because  is always the player and  always the speaker.
# 0x84 and 0x85 are the English articles 'a/an' and 'the', which Russian
# has no use for at all.
DROPPABLE = {
    'DIPLOMSE.LBX': {0x81, 0x82, 0x84, 0x85},
    # GNN copy: / are articles, / the English plural 's',
    # // a race name that Russian can only use as the subject
    'EVENTMSE.LBX': {0x83, 0x84, 0x85, 0x8f, 0x90, 0x91, 0x92},
}


def marks(s):
    return [c for c in s if LOW <= ord(c) <= HIGH]


def scan():
    out = defaultdict(list)
    for jf in sorted(glob.glob(os.path.join(TEXT, '*.json'))):
        d = json.load(open(jf, encoding='utf-8'))
        for e in d['entries']:
            ru = e.get('ru')
            if not ru:
                continue
            drop = DROPPABLE.get(d['file'], ())
            me = [c for c in marks(e['en']) if ord(c) not in drop]
            mr = [c for c in marks(ru) if ord(c) not in drop]
            if sorted(me) != sorted(mr):
                out[(d['file'], ru)].append((e['id'], e['en'], me, mr))
    return out


def main():
    groups = scan()
    n = sum(len(v) for v in groups.values())
    for (f, ru), rows in sorted(groups.items()):
        eid, en, me, mr = rows[0]
        print('%s %s  (%d copies)' % (f, eid, len(rows)))
        print('   en %r' % en)
        print('   ru %r' % ru)
        print('   want %s  have %s' % ([hex(ord(c)) for c in me],
                                       [hex(ord(c)) for c in mr]))
    print('%d strings, %d distinct' % (n, len(groups)))


if __name__ == '__main__':
    main()
