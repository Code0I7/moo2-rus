# -*- coding: utf-8 -*-
"""Build Cyrillic (CP1251) glyphs for the six MOO2 bitmap fonts.

Every new glyph is assembled out of strips taken from the font's own Latin
glyphs, so stroke weight, anti aliasing and (for the big decorated face) the
colour gradient all match the original automatically.

Uppercase letters are drawn with a small stroke DSL inside the cap band;
lowercase small-cap forms are produced by squeezing the uppercase glyph down
to the x-height band.  Letters whose shape is identical to a Latin one are
copied verbatim.
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
from lbx import Lbx
from moo2font import FontFile, NCHARS, NFONTS, OFFS_TBL

# --------------------------------------------------------------------------- helpers

def ink_rows(g):
    r = [i for i, row in enumerate(g) if any(p is not None for p in row)]
    return (min(r), max(r)) if r else (0, 0)


def dense(g, w=None, h=None):
    """glyph -> rectangular grid of (colour|None)."""
    if w is None:
        w = max((len(r) for r in g), default=0)
    if h is None:
        h = len(g)
    out = []
    for y in range(h):
        row = list(g[y]) if y < len(g) else []
        row = row[:w] + [None] * (w - len(row))
        out.append(row)
    return out


def blank(w, h):
    return [[None] * w for _ in range(h)]


def trim_right(grid):
    w = 0
    for row in grid:
        for x, p in enumerate(row):
            if p is not None:
                w = max(w, x + 1)
    return [row[:w] for row in grid], w


class Parts:
    """Measured metrics + reusable strips for one font."""

    def __init__(self, font):
        self.f = font
        self.h = font.height
        G = {c: dense(font.glyphs[ord(c)], font.widths[ord(c)], font.height)
             for c in 'HEONUXTBPRCzon3KMLY' if font.glyphs[ord(c)]}
        self.G = G
        self.capT, self.capB = ink_rows(G['E'])
        self.xT, self.xB = ink_rows(G['o'])
        self.descB = ink_rows(dense(font.glyphs[ord('p')], font.widths[ord('p')], font.height))[1]
        self.UW = font.widths[ord('H')]
        self.EW = font.widths[ord('E')]
        # stem width: leading ink run of H on a row that is not the crossbar
        y = self.capT + 1
        row = G['H'][y]
        sw = 0
        while sw < len(row) and row[sw] is not None:
            sw += 1
        self.sw = max(1, sw)
        # bar thickness: rows of E's top bar, i.e. rows that span most of the width
        tb = 0
        for i in range(self.capB - self.capT + 1):
            row = G['E'][self.capT + i]
            if sum(1 for p in row if p is not None) >= 0.7 * self.EW:
                tb += 1
            else:
                break
        self.tb = max(1, tb)
        # strips (crossbar rows of H / arch rows of n are replaced by a clean one)
        self.stemU = self._clean_stem(G['H'], self.capT, self.capB)
        self.stemL = self._clean_stem(G['n'], self.xT, self.xB)
        self.barU = [G['E'][self.capT + i][:] for i in range(self.tb)]
        zT, zB = ink_rows(G['z'])
        self.barL = [G['z'][zT + i][:] for i in range(min(self.tb, zB - zT + 1))]

    def _clean_stem(self, src, y0, y1):
        """Left stem strip of a two-stem glyph, with joined rows filtered out."""
        w = len(src[0])
        strips = [row[:self.sw] for row in src]
        joined = set()
        for y in range(len(src)):
            middle = src[y][self.sw:max(self.sw, w - self.sw)]
            if any(p is not None for p in middle):
                joined.add(y)
        clean = [tuple(strips[y]) for y in range(y0, y1 + 1)
                 if y not in joined and any(p is not None for p in strips[y])]
        if not clean:
            return strips
        modal = list(max(set(clean), key=clean.count))
        out = []
        for y in range(len(strips)):
            s = strips[y]
            if y in joined or not any(p is not None for p in s):
                out.append(list(modal))
            else:
                out.append(s)
        return out

    # -- colour sampling -----------------------------------------------------
    def stem_px(self, y, k, lower=False):
        strip = self.stemL if lower else self.stemU
        y = max(0, min(len(strip) - 1, y))
        r = strip[y]
        if not r or all(p is None for p in r):
            # fall back to the first fully inked row
            for rr in strip:
                if rr and any(p is not None for p in rr):
                    r = rr
                    break
        k = max(0, min(len(r) - 1, k))
        v = r[k]
        if v is None:
            v = next((p for p in r if p is not None), 2)
        return v

    def bar_px(self, i, x, n, lower=False):
        rows = self.barL if lower else self.barU
        if not rows:
            rows = self.barU
        r = rows[min(i, len(rows) - 1)]
        r = [p for p in r]
        if len(r) < 3:
            return next((p for p in r if p is not None), 2)
        if x == 0:
            v = r[0]
        elif x >= n - 1:
            v = r[-1]
        else:
            v = r[1 + (x - 1) % (len(r) - 2)]
        if v is None:
            v = next((p for p in r if p is not None), 2)
        return v


# --------------------------------------------------------------------------- drawing

class Pen:
    def __init__(self, parts, w, lower=False):
        self.p = parts
        self.w = w
        self.h = parts.h
        self.g = blank(w, parts.h)
        self.lower = lower

    def _set(self, x, y, v):
        if 0 <= x < self.w and 0 <= y < self.h and v is not None:
            self.g[y][x] = v

    def vstem(self, x, y0, y1, sw=None):
        sw = sw or self.p.sw
        for y in range(y0, y1 + 1):
            for k in range(sw):
                self._set(x + k, y, self.p.stem_px(y, k, self.lower))

    def slant(self, xtop, xbot, y0, y1, sw=None):
        sw = sw or self.p.sw
        n = max(1, y1 - y0)
        for y in range(y0, y1 + 1):
            x = int(round(xtop + (xbot - xtop) * (y - y0) / n))
            for k in range(sw):
                self._set(x + k, y, self.p.stem_px(y, k, self.lower))

    def hbar(self, y, x0, x1, tb=None):
        tb = tb or self.p.tb
        n = x1 - x0 + 1
        for i in range(tb):
            for j in range(n):
                self._set(x0 + j, y + i, self.p.bar_px(i, j, n, self.lower))

    def diag(self, x0, y0, x1, y1, sw=None):
        sw = sw or self.p.sw
        steps = max(abs(x1 - x0), abs(y1 - y0))
        if steps == 0:
            steps = 1
        for s in range(steps + 1):
            x = x0 + (x1 - x0) * s / steps
            y = y0 + (y1 - y0) * s / steps
            xi, yi = int(round(x)), int(round(y))
            for k in range(sw):
                self._set(xi + k, yi, self.p.stem_px(yi, k, self.lower))

    def box(self, x0, y0, x1, y1, cut=None):
        """rectangle outline with the sharp corners knocked off"""
        if cut is None:
            cut = 1 if self.p.sw <= 2 else self.p.sw // 2
        self.hbar(y0, x0, x1)
        self.hbar(y1 - self.p.tb + 1, x0, x1)
        self.vstem(x0, y0, y1)
        self.vstem(x1 - self.p.sw + 1, y0, y1)
        for i in range(cut):
            for j in range(cut - i):
                for (cx, dx) in ((x0, 1), (x1, -1)):
                    for (cy, dy) in ((y0, 1), (y1, -1)):
                        self._set(cx + dx * j, cy + dy * i, None)
                        if 0 <= cx + dx * j < self.w and 0 <= cy + dy * i < self.h:
                            self.g[cy + dy * i][cx + dx * j] = None

    def result(self):
        return self.g


# --------------------------------------------------------------------------- recipes

def build_upper(P, ch):
    """Return a dense grid for one uppercase Cyrillic letter, or None."""
    sw, tb = P.sw, P.tb
    T, B = P.capT, P.capB
    mid = T + (B - T) // 2 - (tb // 2)
    midC = T + int(round((B - T) * 0.42))
    ft = min(tb, P.h - 1 - B)              # tail length below the baseline
    UW, EW = P.UW, P.EW
    gap = max(1, UW - 2 * sw)
    gapS = max(1, int(round(gap * 0.7)))    # tighter gap for three-stem letters
    NW = max(sw + 2, EW)                    # narrow letters
    W3 = 3 * sw + 2 * gapS                  # Ш / Щ
    ind = 1 if sw <= 2 else sw // 2
    # Ь, Ы and Ъ need a visible stretch of bare stem above the bowl, otherwise
    # the bowl reads as an О with a stick next to it - the lower case letters
    # are squeezed into the x-height band and lose that stem first.
    soft = T + int(round((B - T) * 0.52))
    # Л leans its left leg well over; a one pixel offset just looks like П
    lind = max(2, (UW - sw) * 2 // 5)

    def pen(w):
        return Pen(P, w)

    if ch == 'Б':
        p = pen(NW); w = NW - 1
        p.vstem(0, T, B); p.hbar(T, 0, w); p.hbar(mid, 0, w); p.hbar(B - tb + 1, 0, w)
        p.vstem(w - sw + 1, mid, B)
        return p.result()
    if ch == 'Г':
        p = pen(NW); w = NW - 1
        p.vstem(0, T, B); p.hbar(T, 0, w)
        return p.result()
    if ch == 'Д':
        W = UW + ind; p = pen(W); w = W - 1
        p.hbar(T, ind, w - 0)
        p.vstem(ind, T, B - tb)
        p.vstem(w - sw + 1, T, B - tb)
        p.hbar(B - tb + 1, 0, w)
        if ft:
            p.vstem(0, B + 1, B + ft)
            p.vstem(w - sw + 1, B + 1, B + ft)
        return p.result()
    if ch == 'Ж':
        W = UW + 2 * sw + max(1, gap // 3); p = pen(W); w = W - 1
        cx = (W - sw) // 2
        cy = T + (B - T) // 2
        p.diag(0, T, cx, cy); p.diag(0, B, cx, cy)
        p.diag(w - sw + 1, T, cx, cy); p.diag(w - sw + 1, B, cx, cy)
        p.vstem(cx, T, B)
        return p.result()
    if ch == 'И':
        p = pen(UW); w = UW - 1
        p.vstem(0, T, B); p.vstem(w - sw + 1, T, B)
        p.diag(0, B, w - sw + 1, T)
        p.vstem(0, T, B); p.vstem(w - sw + 1, T, B)
        return p.result()
    if ch == 'Л':
        p = pen(UW); w = UW - 1
        p.hbar(T, lind, w)
        p.slant(lind, 0, T, B)
        p.vstem(w - sw + 1, T, B)
        return p.result()
    if ch == 'П':
        p = pen(UW); w = UW - 1
        p.vstem(0, T, B); p.vstem(w - sw + 1, T, B); p.hbar(T, 0, w)
        return p.result()
    if ch == 'У':
        # not the Latin Y: the right arm runs on down to the bottom left
        # corner and the left arm only reaches it a little below the middle
        p = pen(UW); w = UW - 1
        xr0, xr1 = w - sw + 1, 0
        m = T + int(round((B - T) * 0.6))
        xm = int(round(xr0 + (xr1 - xr0) * (m - T) / max(1, B - T)))
        p.diag(xr0, T, xr1, B)
        p.diag(0, T, xm, m)
        return p.result()
    if ch == 'Ф':
        W = UW + ind; p = pen(W); w = W - 1
        cx = (W - sw) // 2
        p.box(0, T + (1 if B - T > 6 else 0), w, B - (1 if B - T > 6 else 0))
        p.vstem(cx, T, B)
        return p.result()
    if ch == 'Ц':
        W = UW + (ind if ft else 0); p = pen(W); w = W - 1
        p.vstem(0, T, B - tb); p.vstem(w - sw + 1 - (ind if ft else 0), T, B - tb)
        p.hbar(B - tb + 1, 0, w - (ind if ft else 0))
        if ft:
            p.vstem(w - sw + 1, B + 1, B + ft)
        return p.result()
    if ch == 'Ч':
        p = pen(UW); w = UW - 1
        p.vstem(0, T, midC + tb - 1); p.vstem(w - sw + 1, T, B); p.hbar(midC, 0, w)
        return p.result()
    if ch == 'Ш':
        W = W3; p = pen(W); w = W - 1
        cx = (W - sw) // 2
        p.vstem(0, T, B - tb); p.vstem(cx, T, B - tb); p.vstem(w - sw + 1, T, B - tb)
        p.hbar(B - tb + 1, 0, w)
        return p.result()
    if ch == 'Щ':
        W = W3 + (ind if ft else 0); p = pen(W); w = W - 1
        e = w - (ind if ft else 0)
        # midway between the outer stems (0 and e - sw + 1); (e - sw) // 2
        # put it one pixel left whenever that span was odd, and in the small
        # faces glued it to the left stem so щ read as ц
        cx = (e - sw + 1) // 2
        p.vstem(0, T, B - tb); p.vstem(cx, T, B - tb); p.vstem(e - sw + 1, T, B - tb)
        p.hbar(B - tb + 1, 0, e)
        if ft:
            p.vstem(w - sw + 1, B + 1, B + ft)
        return p.result()
    if ch == 'Ъ':
        W = NW + ind; p = pen(W); w = W - 1
        p.hbar(T, 0, ind + sw - 1)
        p.vstem(ind, T, B)
        p.hbar(soft, ind, w); p.hbar(B - tb + 1, ind, w)
        p.vstem(w - sw + 1, soft, B)
        return p.result()
    if ch == 'Ь':
        p = pen(NW); w = NW - 1
        p.vstem(0, T, B); p.hbar(soft, 0, w); p.hbar(B - tb + 1, 0, w)
        p.vstem(w - sw + 1, soft, B)
        return p.result()
    if ch == 'Ы':
        W = NW + max(1, gap // 2) + sw; p = pen(W); w = W - 1
        e = NW - 1
        p.vstem(0, T, B); p.hbar(soft, 0, e); p.hbar(B - tb + 1, 0, e)
        p.vstem(e - sw + 1, soft, B)
        p.vstem(w - sw + 1, T, B)
        return p.result()
    if ch == 'Э':
        p = pen(UW); w = UW - 1
        cx = max(sw, (UW - sw) // 2)
        p.hbar(T, 0, w); p.hbar(B - tb + 1, 0, w)
        p.vstem(w - sw + 1, T, B)
        p.hbar(mid, cx, w)
        return p.result()
    if ch == 'Ю':
        W = UW + sw + ind; p = pen(W); w = W - 1
        p.vstem(0, T, B)
        p.box(sw + ind, T, w, B)
        p.hbar(mid, sw, sw + ind)
        return p.result()
    if ch == 'Я':
        p = pen(UW); w = UW - 1
        p.vstem(w - sw + 1, T, B)
        p.hbar(T, 0, w); p.hbar(mid, 0, w)
        p.vstem(0, T, mid)
        p.diag(w - sw, mid, 0, B)
        p.vstem(w - sw + 1, T, B)
        return p.result()
    return None


# letters that are simply a Latin glyph
SAME_UPPER = {'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O',
              'Р': 'P', 'С': 'C', 'Т': 'T', 'Х': 'X', 'З': '3'}
SAME_LOWER = {'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x'}

UPPER = 'АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
LOWER = 'абвгдежзиклмнопрстуфхцчшщъыьэюя'

CP1251 = {}
for i, c in enumerate(UPPER):
    CP1251[c] = 0xC0 + i if i < 9 else None
# build the real cp1251 map from python's codec instead
CP1251 = {c: c.encode('cp1251')[0] for c in
          (UPPER + LOWER + 'ЙйЁё')}


def squeeze(grid, band_from, band_to, keep_below=True):
    """Compress rows [band_from] to the height of [band_to] and move them there."""
    (f0, f1), (t0, t1) = band_from, band_to
    src = grid[f0:f1 + 1]
    need = t1 - t0 + 1
    rows = list(range(len(src)))
    while len(rows) > need and len(rows) > 2:
        # drop the interior row most similar to its predecessor
        best, bi = None, None
        for i in range(1, len(rows) - 1):
            a, b = src[rows[i - 1]], src[rows[i]]
            d = sum(1 for x in range(len(b)) if (a[x] is None) != (b[x] is None))
            if best is None or d < best:
                best, bi = d, i
        rows.pop(bi)
    while len(rows) < need:
        rows.insert(len(rows) // 2, rows[len(rows) // 2])
    w = len(grid[0])
    out = blank(w, len(grid))
    for i, r in enumerate(rows):
        out[t0 + i] = list(src[r])
    if keep_below:
        for y in range(f1 + 1, len(grid)):
            ny = t1 + (y - f1)
            if ny < len(grid):
                for x in range(w):
                    if grid[y][x] is not None:
                        out[ny][x] = grid[y][x]
    return out


def add_breve(P, grid, w):
    """small breve / dieresis row above the letter (row 0)"""
    return grid


def make_font_cyr(font):
    P = Parts(font)
    res = {}
    # ---- uppercase
    for ch in UPPER:
        if ch in SAME_UPPER:
            src = SAME_UPPER[ch]
            res[ch] = dense(font.glyphs[ord(src)], font.widths[ord(src)], font.height)
        else:
            g = build_upper(P, ch)
            if g is not None:
                res[ch] = g
    # ---- lowercase
    for ch in LOWER:
        if ch in SAME_LOWER:
            src = SAME_LOWER[ch]
            res[ch] = dense(font.glyphs[ord(src)], font.widths[ord(src)], font.height)
            continue
        up = res.get(ch.upper())
        if up is None:
            continue
        res[ch] = squeeze(up, (P.capT, P.capB), (P.xT, P.xB))
    # б : latin 'b' plus a flag on the ascender
    b = dense(font.glyphs[ord('b')], font.widths[ord('b')], font.height)
    bT = ink_rows(b)[0]
    pb = Pen(P, len(b[0]))
    pb.g = [list(r) for r in b]
    pb.hbar(bT, P.sw, len(b[0]) - 1)
    res['б'] = pb.result()
    # guillemets: two copies of the Latin angle brackets, one pixel apart
    for src, ch in (('<', '«'), ('>', '»')):
        g = dense(font.glyphs[ord(src)], font.widths[ord(src)], font.height)
        w = len(g[0])
        gap = 1 if P.sw <= 2 else P.sw // 2
        out = blank(w * 2 + gap, font.height)
        for y in range(font.height):
            for x in range(w):
                if g[y][x] is not None:
                    out[y][x] = g[y][x]
                    out[y][x + w + gap] = g[y][x]
        res[ch] = out
    # en and em dash: the Latin hyphen stretched.  The original fonts have no
    # glyph at CP1251 0x96/0x97, so every "—" in the translation used to print
    # as nothing ("в этот славный день  день первой встречи")
    h = dense(font.glyphs[ord('-')], font.widths[ord('-')], font.height)
    cols = [x for x in range(len(h[0])) if any(r[x] is not None for r in h)]
    if cols:
        x0, x1 = cols[0], cols[-1]
        ink = x1 - x0 + 1
        for ch, n in (('–', ink + max(1, ink // 2)), ('—', ink * 2 + 1)):
            out = []
            for r in h:
                seg = r[x0:x1 + 1]
                if all(p is None for p in seg):
                    out.append(r[:x0] + [None] * n)
                    continue
                mid = seg[len(seg) // 2]
                body = [seg[0]] + [mid] * (n - 2) + [seg[-1]] if n >= 2 else [mid] * n
                out.append(r[:x0] + body)
            res[ch] = out
    # Й / й  and  Ё / ё : squeeze the base letter by one row and add the mark
    for base, ch in (('И', 'Й'), ('Е', 'Ё')):
        g = res[base]
        g2 = squeeze(g, (P.capT, P.capB), (P.capT + 1, P.capB))
        w = len(g2[0])
        mark_y = P.capT
        if ch == 'Й':
            for x in range(max(1, w // 4), min(w - 1, w - 1 - w // 4) + 1):
                g2[mark_y][x] = P.stem_px(mark_y, 0)
        else:
            for x in (max(0, w // 4), min(w - 1, w - 1 - w // 4)):
                for k in range(max(1, P.sw - 1)):
                    if 0 <= x + k < w:
                        g2[mark_y][x + k] = P.stem_px(mark_y, 0)
        res[ch] = g2
    for base, ch in (('и', 'й'), ('е', 'ё')):
        g = [list(r) for r in res[base]]
        w = len(g[0])
        top = ink_rows(g)[0]
        my = max(0, top - (2 if P.sw > 1 else 1))
        if ch == 'й':
            for x in range(max(1, w // 4), min(w - 1, w - 1 - w // 4) + 1):
                g[my][x] = P.stem_px(my, 0, True)
        else:
            for x in (max(0, w // 4), min(w - 1, w - 1 - w // 4)):
                for k in range(max(1, P.sw - 1)):
                    if 0 <= x + k < w:
                        g[my][x + k] = P.stem_px(my, 0, True)
        res[ch] = g
    return res


def apply(fontfile):
    for font in fontfile.fonts:
        cyr = make_font_cyr(font)
        used = set()
        for ch, grid in cyr.items():
            code = ch.encode('cp1251')[0]
            grid, w = trim_right(grid)
            if w == 0:
                continue
            font.glyphs[code] = grid
            font.widths[code] = w
            used.add(code)
        # every remaining code above 0x7F gets an explicit empty glyph of zero
        # width, so the engine's text substitution markers (0x80-0x95) stay
        # invisible once the character limit in the EXE has been raised
        empty = [[] for _ in range(24)]
        for code in range(0x7F, 0x100):
            if code not in used:
                font.glyphs[code] = empty
                font.widths[code] = 0
    return fontfile


def main():
    root = ROOT
    bak = os.path.join(PROJ, 'backup')
    out = os.path.join(root, '150', 'mods', 'rus', 'lbx')
    os.makedirs(bak, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    for name in ('FONTS.LBX', 'IFONTS.LBX'):
        orig = os.path.join(bak, name + '.orig')
        if not os.path.exists(orig):
            import shutil
            shutil.copyfile(os.path.join(root, name), orig)
        L = Lbx.load(orig)
        F = FontFile(L.items[0])
        apply(F)
        entry0 = F.build()
        # Print_Clipped_Letter_ reads the glyph offset as a 16 bit word, so the
        # whole glyph area has to fit in 64K or the headings on the Tech Review
        # and Race Statistics screens turn into a smear again.
        import struct as _s
        top = max(max(_s.unpack_from('<%dI' % NCHARS, entry0, OFFS_TBL + fi * 0x400))
                  for fi in range(NFONTS))
        if top >= 0x10000:
            raise SystemExit('%s: glyph area reaches 0x%x, must stay under 0x10000 '
                             '- see patchexe.py GLYPH_AREA_LIMIT' % (name, top))
        L.items[0] = entry0
        dst = os.path.join(out, name)
        L.save(dst)
        print('wrote %s (glyph area 0x%05x of 0x10000)' % (dst, top))


if __name__ == '__main__':
    main()
