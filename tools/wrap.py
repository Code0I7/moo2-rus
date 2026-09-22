# -*- coding: utf-8 -*-
"""Word-wrap simulator for the game's paragraph printer.

Print_Paragraph_ fills a line word by word and breaks before the first word
that would cross the right edge; a hard newline always breaks.  The pen
advance per character is widths[ch] + spacing[font] (see width.py), so the
same arithmetic tells how many lines a text takes in a given box.

The boxes below were measured from 640x480 screenshots against known line
breaks (see calibrate() for the evidence each one rests on).
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from width import load_fonts, width, SPACING, CTRL, enc

# name: (font, width px, max lines)
BOX = {
    # INFO -> Tech Review, description under the picture
    'techreview': (2, 174, 11),
    # INFO -> Reference, topic page (justified).  Measured width 383-387 px;
    # line 19 still fits but touches the RETURN frame, line 20 hits BACK
    'reference': (4, 384, 18),
}

_F = None


def fonts():
    global _F
    if _F is None:
        _F = load_fonts()
    return _F


def wrap(s, fi, w):
    """-> list of lines (strings) the way the engine would break them"""
    F = fonts()
    f = F.fonts[fi]

    def cw(ch):
        b = enc(ch)
        return sum(0 if x in CTRL else f.widths[x] + SPACING[fi] for x in b)

    out = []
    for para in s.split('\n'):
        line, lw = '', 0
        for word in para.split(' '):
            ww = sum(cw(c) for c in word)
            if line == '' and lw == 0:
                cand = ww
            else:
                cand = lw + cw(' ') + ww
            if cand <= w or (line == '' and lw == 0):
                line = word if (line == '' and lw == 0) else line + ' ' + word
                lw = cand
            else:
                out.append(line)
                line, lw = word, ww
        out.append(line)
    return out


def lines(s, box):
    fi, w, _ = BOX[box]
    return len(wrap(s, fi, w))


def fits(s, box):
    return lines(s, box) <= BOX[box][2]


def calibrate():
    """print the range of box widths consistent with observed line breaks"""
    seen = {
        2: [['Хранит новейшее', 'вычислительное', 'оборудование, создавая',
             'превосходные условия для', 'науки. Даёт 5 очков науки и',
             'повышает отдачу каждого', 'учёного на +1.'],
            ['Позволяют строить', 'транспортные корабли и', 'готовят пехоту для',
             'защиты от вторжения. При', 'постройке дают до 4',
             'единиц, затем готовят 1', 'единицу каждые 5 ходов,',
             'вплоть до половины', 'населения планеты.', 'Снимают штраф к морали',
             'при феодализме и'],
            ['Утраивает прочность', 'корпуса корабля и лучше', 'защищает двигательную',
             'установку: чтобы её', 'уничтожить, нужно втрое', 'больше урона.']],
    }
    F = fonts()
    for fi, texts in seen.items():
        lo, hi = 0, 10 ** 6
        for ls in texts:
            for a, b in zip(ls, ls[1:]):
                wa = width(F, fi, a)
                nxt = b.split(' ')[0]
                lo = max(lo, wa)
                hi = min(hi, width(F, fi, a + ' ' + nxt) - 1)
            lo = max(lo, width(F, fi, ls[-1]))
        print('font %d: width in [%d, %d]' % (fi, lo, hi))


if __name__ == '__main__':
    calibrate()
