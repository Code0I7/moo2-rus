# -*- coding: utf-8 -*-
"""Extract / inject text in Master of Orion 2 LBX files.

Three storage shapes are handled:

* fields  - the record is a fixed-size struct/slot; every C string keeps its
            own offset and may grow into the NUL padding that follows it.
* pool    - the record is a tightly packed list of C strings; the whole record
            is repacked, the only limit is the record size.
* rawpool - the LBX sub-file is a bare list of C strings (TECHNAME.LBX).
"""
import struct, os, re

POOL_FILES = {'ESTRINGS.LBX', 'RSTRING0.LBX', 'HESTRNGS.LBX', 'MAINTEXT.LBX'}
# RACESTUF / PLAYSPEC / CUSTMSTR keep the race trait labels as one packed list
# of C strings per language, with no record table in front of them
RAWPOOL_FILES = {'TECHNAME.LBX', 'RACESTUF.LBX', 'PLAYSPEC.LBX', 'CUSTMSTR.LBX'}

PRINT = set(range(0x20, 0x7f))


def strtab(it):
    """(count, size) if the sub-file is a fixed-size record table."""
    if len(it) < 6:
        return None
    c, s = struct.unpack_from('<HH', it, 0)
    if c and s and 4 + c * s == len(it):
        return c, s
    return None


def runs(rec):
    """Yield (offset, text_bytes, capacity) for every C string inside rec.

    capacity is how many bytes the string may occupy (terminator excluded):
    it extends over the NUL padding up to the next non-zero byte.
    """
    n = len(rec)
    i = 0
    while i < n:
        b = rec[i]
        if b in PRINT or b >= 0x80:
            j = i
            while j < n and rec[j] != 0:
                j += 1
            text = rec[i:j]
            k = j
            while k < n and rec[k] == 0:
                k += 1
            cap = (k - i - 1) if k < n else (n - i - 1)
            if re.search(rb'[A-Za-z]', text):
                yield i, text, max(cap, len(text))
            i = k
        else:
            i += 1


def extract(path):
    from lbx import Lbx
    name = os.path.basename(path).upper()
    L = Lbx.load(path)
    mode = 'rawpool' if name in RAWPOOL_FILES else ('pool' if name in POOL_FILES else 'fields')
    entries = []
    for ii, it in enumerate(L.items):
        if mode == 'rawpool':
            for pi, s in enumerate(it.split(b'\x00')):
                if s:
                    entries.append({'id': '%d/%d' % (ii, pi), 'cap': 0, 'en': s.decode('latin1')})
            continue
        st = strtab(it)
        if not st:
            continue
        c, s = st
        body = it[4:]
        for ri in range(c):
            rec = body[ri * s:(ri + 1) * s]
            if mode == 'pool':
                for pi, p in enumerate(rec.split(b'\x00')):
                    if p:
                        entries.append({'id': '%d/%d/%d' % (ii, ri, pi), 'cap': 0,
                                        'en': p.decode('latin1')})
            else:
                for off, text, cap in runs(rec):
                    entries.append({'id': '%d/%d/%d' % (ii, ri, off), 'cap': cap,
                                    'en': text.decode('latin1')})
    return mode, entries


def inject(path, mode, trans, out_path, grow=0):
    """trans: dict id -> russian text already encoded in cp1251 -> latin1 str."""
    from lbx import Lbx
    L = Lbx.load(path)
    stats = {'ok': 0, 'trunc': 0, 'overflow': []}
    for ii, it in enumerate(L.items):
        if mode == 'rawpool':
            parts = it.split(b'\x00')
            newp = []
            for pi, s in enumerate(parts):
                key = '%d/%d' % (ii, pi)
                if s and key in trans:
                    newp.append(trans[key].encode('latin1'))
                    stats['ok'] += 1
                else:
                    newp.append(s)
            L.items[ii] = b'\x00'.join(newp)
            continue
        st = strtab(it)
        if not st:
            continue
        c, s = st
        body = bytearray(it[4:])
        if mode == 'pool':
            ns = s + grow
            out = bytearray()
            for ri in range(c):
                rec = bytes(body[ri * s:(ri + 1) * s])
                parts = []
                for pi, p in enumerate(rec.split(b'\x00')):
                    key = '%d/%d/%d' % (ii, ri, pi)
                    if p and key in trans:
                        p = trans[key].encode('latin1')
                        stats['ok'] += 1
                    parts.append(p)
                # the tail of the record is NUL padding, not empty strings
                while parts and not parts[-1]:
                    parts.pop()
                buf = bytearray(b'\x00'.join(parts))
                if len(buf) > ns:
                    stats['overflow'].append((ii, ri, len(buf), ns))
                    buf = buf[:ns]
                out += buf + b'\x00' * (ns - len(buf))
            L.items[ii] = struct.pack('<HH', c, ns) + bytes(out)
        else:
            for ri in range(c):
                base = ri * s
                rec = bytes(body[base:base + s])
                for off, text, cap in runs(rec):
                    key = '%d/%d/%d' % (ii, ri, off)
                    if key not in trans:
                        continue
                    nb = trans[key].encode('latin1')
                    if len(nb) > cap:
                        stats['overflow'].append((ii, ri, off, len(nb), cap))
                        nb = nb[:cap]
                        stats['trunc'] += 1
                    else:
                        stats['ok'] += 1
                    body[base + off:base + off + cap + 1] = nb + b'\x00' * (cap + 1 - len(nb))
            L.items[ii] = struct.pack('<HH', c, s) + bytes(body)
    d = os.path.dirname(out_path)
    if d:
        os.makedirs(d, exist_ok=True)
    L.save(out_path)
    return stats
