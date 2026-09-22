"""MOO2 FONTS.LBX / IFONTS.LBX font codec.

Entry 0 layout (little endian):
  0x0000  header (12 bytes + misc)
  0x059C  6 x 256-byte width tables            (width_table[font][char])
  0x0B9C  6 x 256-dword glyph offset tables    (offset_table[font][char])
  0x239C  glyph data, offsets are relative to this base

Glyph encoding: row major.
  0x80        -> end of row
  0x81..0xFF  -> skip (b - 0x80) transparent pixels
  0x00..0x7F  -> one pixel with colour index b
"""
import struct

WIDTH_TBL = 0x059C
OFFS_TBL = 0x0B9C
HEIGHT_TBL = 0x056C
GLYPH_BASE = 0x239C
NFONTS = 6
NCHARS = 256


class Font:
    __slots__ = ('height', 'widths', 'glyphs')

    def __init__(self, height, widths, glyphs):
        self.height = height
        self.widths = widths      # list[256] of int
        self.glyphs = glyphs      # list[256] of list[rows][list of (color or None)]


def decode_glyph(blob):
    rows, cur = [], []
    for b in blob:
        if b == 0x80:
            rows.append(cur); cur = []
        elif b > 0x80:
            cur.extend([None] * (b - 0x80))
        else:
            cur.append(b)
    if cur:
        rows.append(cur)
    return rows


def encode_glyph(rows):
    out = bytearray()
    for row in rows:
        # strip trailing transparent
        r = list(row)
        while r and r[-1] is None:
            r.pop()
        i = 0
        while i < len(r):
            if r[i] is None:
                j = i
                while j < len(r) and r[j] is None:
                    j += 1
                n = j - i
                while n > 0:
                    k = min(n, 0x7F)
                    out.append(0x80 + k)
                    n -= k
                i = j
            else:
                out.append(r[i] & 0x7F)
                i += 1
        out.append(0x80)
    return bytes(out)


def _rows(blob, at, height):
    """decode exactly `height` rows starting at `at`, the way the engine does"""
    rows, cur, i = [], [], at
    n = len(blob)
    while len(rows) < height and i < n:
        b = blob[i]; i += 1
        if b == 0x80:
            rows.append(cur); cur = []
        elif b > 0x80:
            cur.extend([None] * (b - 0x80))
        else:
            cur.append(b)
    while len(rows) < height:
        rows.append([])
    return rows


class FontFile:
    def __init__(self, entry0: bytes):
        self.raw = entry0
        self.fonts = []
        for fi in range(NFONTS):
            wt = WIDTH_TBL + fi * 0x100
            ot = OFFS_TBL + fi * 0x400
            widths = list(entry0[wt:wt + NCHARS])
            offs = list(struct.unpack_from('<%dI' % NCHARS, entry0, ot))
            # each table holds only 256 entries, so char 255 has no end offset of
            # its own: it borrows the next font's first entry (the glyph data of
            # every font is stored back to back, char 255 last).
            if fi + 1 < NFONTS:
                offs.append(struct.unpack_from('<I', entry0, OFFS_TBL + (fi + 1) * 0x400)[0])
            else:
                offs.append(len(entry0) - GLYPH_BASE)
            glyphs = [None] * NCHARS
            # A glyph has no stored length: the engine simply decodes `height`
            # rows and stops, which is what lets several characters share the
            # same bytes (see build()).  Deriving the end from the next
            # character's offset only works while the data is laid out in
            # order, so read the height table and decode row by row instead.
            height = struct.unpack_from('<H', entry0, HEIGHT_TBL + fi * 2)[0]
            for c in range(0, NCHARS):
                if c >= 127 and not widths[c]:
                    continue
                a = offs[c]
                if GLYPH_BASE + a >= len(entry0):
                    continue
                glyphs[c] = _rows(entry0, GLYPH_BASE + a, height)
            self.fonts.append(Font(height, widths, glyphs))

    def header(self):
        return self.raw[:WIDTH_TBL]

    def build(self):
        """Re-serialise. Glyph data is rebuilt from self.fonts.

        Identical glyphs share one copy of their bytes.  Adding Cyrillic more
        than doubles the glyph area, and two of the engine's drawing routines
        hold the offset in 16 bits (see tools/patchexe.py), so everything
        has to stay under 64K.  Sharing costs nothing: most of the alphabet is
        blank placeholders, and eleven capitals plus seven lower case letters
        are drawn exactly like their Latin twins.
        """
        head = bytearray(self.raw[:GLYPH_BASE])
        data = bytearray()
        seen = {}
        for fi, f in enumerate(self.fonts):
            wt = WIDTH_TBL + fi * 0x100
            ot = OFFS_TBL + fi * 0x400
            offs = []
            for c in range(NCHARS):
                g = f.glyphs[c]
                blob = encode_glyph(g) if g else b''
                at = seen.get(blob)
                if at is None:
                    at = len(data)
                    seen[blob] = at
                    data += blob
                offs.append(at)
                head[wt + c] = f.widths[c] & 0xFF
            offs.append(len(data))
            struct.pack_into('<%dI' % NCHARS, head, ot, *offs[:NCHARS])
        return bytes(head) + bytes(data)
