"""Minimal LBX (Microprose archive) reader/writer for Master of Orion 2."""
import struct, os

MAGIC = 0x0000FEAD

class Lbx:
    def __init__(self, data: bytes):
        self.raw = data
        cnt, magic, typ = struct.unpack_from('<HIH', data, 0)
        assert magic == MAGIC, 'not an LBX file (magic=%08x)' % magic
        self.count = cnt
        self.type = typ
        self.offsets = list(struct.unpack_from('<%dI' % (cnt + 1), data, 8))
        # everything between the offset table and offsets[0] is the header blob
        self.header_blob = data[8 + 4 * (cnt + 1): self.offsets[0]]
        self.items = [data[self.offsets[i]:self.offsets[i + 1]] for i in range(cnt)]

    @classmethod
    def load(cls, path):
        with open(path, 'rb') as f:
            return cls(f.read())

    def build(self) -> bytes:
        cnt = len(self.items)
        head_len = 8 + 4 * (cnt + 1) + len(self.header_blob)
        offs, cur = [], head_len
        for it in self.items:
            offs.append(cur); cur += len(it)
        offs.append(cur)
        out = bytearray()
        out += struct.pack('<HIH', cnt, MAGIC, self.type)
        out += struct.pack('<%dI' % (cnt + 1), *offs)
        out += self.header_blob
        for it in self.items:
            out += it
        return bytes(out)

    def save(self, path):
        with open(path, 'wb') as f:
            f.write(self.build())


def is_strtab(blob: bytes):
    """Return (count, size) if blob looks like a MOO2 fixed-width string table."""
    if len(blob) < 4:
        return None
    cnt, size = struct.unpack_from('<HH', blob, 0)
    if cnt == 0 or size == 0 or size > 4096 or cnt > 20000:
        return None
    if 4 + cnt * size != len(blob):
        return None
    return cnt, size


def read_strtab(blob: bytes):
    cnt, size = struct.unpack_from('<HH', blob, 0)
    out = []
    for i in range(cnt):
        rec = blob[4 + i * size: 4 + (i + 1) * size]
        out.append(rec)
    return cnt, size, out


def write_strtab(size: int, records):
    out = bytearray(struct.pack('<HH', len(records), size))
    for r in records:
        r = r[:size]
        out += r + b'\x00' * (size - len(r))
    return bytes(out)
