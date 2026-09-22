# -*- coding: utf-8 -*-
"""MOO2 LBX image codec.

Sub-file layout:

    u16 width
    u16 height
    u16 unknown (0)
    u16 frame count
    u16 frame delay
    u16 flags            0x1000 = an internal 256 colour palette follows
    u32 offsets[frames+1]
    [palette: u16 first, u16 count, then count * (r,g,b,0) in 6 bit VGA]
    frame data

A frame is a run length encoded list of rows:

    u16 type             1 everywhere in the shipped data
    repeat:
        u16 advance      rows to skip; >= 1000 ends the frame
        repeat:
            u16 length   0 ends the row
            u16 skip     transparent pixels before the run
            length bytes of palette indices, padded to an even count

The row cursor starts at 0 and moves by skip + length for every run, so a
frame only stores the pixels it actually paints; everything else stays
transparent (or keeps whatever the previous frame left there).
"""
import struct

END = 1000


class Image:
    def __init__(self, w, h, nframes=1, delay=0, flags=0):
        self.w, self.h = w, h
        self.delay, self.flags = delay, flags
        self.unknown = 0
        self.palette = None          # list of (r, g, b) 0..63, or None
        self.pal_first = 0
        # frames[i][y][x] = palette index or None for "not painted"
        self.frames = [[[None] * w for _ in range(h)] for _ in range(nframes)]

    # ---------------------------------------------------------------- read
    @classmethod
    def parse(cls, data):
        w, h, unk, nf, delay, flags = struct.unpack_from('<6H', data, 0)
        img = cls(w, h, nf, delay, flags)
        img.unknown = unk
        offs = list(struct.unpack_from('<%dI' % (nf + 1), data, 12))
        if flags & 0x1000:
            first, cnt = struct.unpack_from('<2H', data, 12 + 4 * (nf + 1))
            base = 12 + 4 * (nf + 1) + 4
            img.pal_first = first
            img.palette = [tuple(data[base + i * 4: base + i * 4 + 3])
                           for i in range(cnt)]
        for i in range(nf):
            img.frames[i] = img._parse_frame(data, offs[i], offs[i + 1],
                                             img.frames[i - 1] if i else None)
        return img

    def _parse_frame(self, data, start, stop, prev):
        rows = [list(r) for r in prev] if prev else \
               [[None] * self.w for _ in range(self.h)]
        p = start
        typ = struct.unpack_from('<H', data, p)[0]
        p += 2
        if typ != 1:
            raise ValueError('unsupported frame type %d' % typ)
        y = 0
        while p + 2 <= stop:
            adv = struct.unpack_from('<H', data, p)[0]
            p += 2
            if adv >= END:
                break
            y += adv
            x = 0
            while True:
                ln = struct.unpack_from('<H', data, p)[0]
                p += 2
                if ln == 0:
                    break
                skip = struct.unpack_from('<H', data, p)[0]
                p += 2
                x += skip
                for k in range(ln):
                    if 0 <= y < self.h and 0 <= x + k < self.w:
                        rows[y][x + k] = data[p + k]
                p += ln + (ln & 1)
                x += ln
        return rows

    # --------------------------------------------------------------- write
    def build(self):
        nf = len(self.frames)
        bodies = []
        for i, fr in enumerate(self.frames):
            bodies.append(self._build_frame(fr, self.frames[i - 1] if i else None))
        head = bytearray(struct.pack('<6H', self.w, self.h, self.unknown,
                                     nf, self.delay, self.flags))
        head += b'\x00' * (4 * (nf + 1))
        if self.palette is not None:
            head += struct.pack('<2H', self.pal_first, len(self.palette))
            for r, g, b in self.palette:
                head += bytes((r, g, b, 0))
        offs, cur = [], len(head)
        for b in bodies:
            offs.append(cur)
            cur += len(b)
        offs.append(cur)
        struct.pack_into('<%dI' % (nf + 1), head, 12, *offs)
        return bytes(head) + b''.join(bodies)

    def _build_frame(self, rows, prev):
        out = bytearray(struct.pack('<H', 1))
        last = -1
        for y in range(self.h):
            row = rows[y]
            if prev is not None and row == list(prev[y]):
                continue            # unchanged rows are simply not stored
            runs, x = [], 0
            while x < self.w:
                if row[x] is None:
                    x += 1
                    continue
                s = x
                while x < self.w and row[x] is not None:
                    x += 1
                runs.append((s, bytes(row[s:x])))
            if not runs:
                continue
            out += struct.pack('<H', y - last if last >= 0 else y)
            last = y
            cur = 0
            for s, payload in runs:
                out += struct.pack('<2H', len(payload), s - cur)
                out += payload
                if len(payload) & 1:
                    out += b'\x00'
                cur = s + len(payload)
            out += struct.pack('<H', 0)
        out += struct.pack('<H', END)
        out += b'\x00\x00'
        return bytes(out)

    # ------------------------------------------------------------- helpers
    def rgb_palette(self, fallback=None):
        pal = fallback or [(0, 0, 0)] * 256
        pal = list(pal)
        if self.palette:
            for i, c in enumerate(self.palette):
                if self.pal_first + i < 256:
                    pal[self.pal_first + i] = c
        return [(r * 255 // 63, g * 255 // 63, b * 255 // 63) for r, g, b in pal]


def looks_like_image(data):
    if len(data) < 20:
        return False
    w, h, unk, nf, delay, flags = struct.unpack_from('<6H', data, 0)
    if not (0 < w <= 640 and 0 < h <= 480 and 0 < nf <= 256 and unk == 0):
        return False
    try:
        offs = struct.unpack_from('<%dI' % (nf + 1), data, 12)
    except struct.error:
        return False
    return offs[0] >= 12 + 4 * (nf + 1) and offs[-1] == len(data) and \
        all(offs[i] <= offs[i + 1] for i in range(nf))
