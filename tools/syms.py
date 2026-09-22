# -*- coding: utf-8 -*-
"""Symbol table of ORION150.EXE plus a small disassembly helper.

The 1.50 patch appends a Watcom-style symbol blob after the LE image.
Record layout: <u32 addr><u16><u16><u8 kind><u8 namelen><name>
Linear address -> file offset is addr + DELTA (verified by matching symbol
addresses against Watcom function prologues).
"""
import struct, re, sys, os

EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ORION150.EXE')
DELTA = 0x9569E


def load(path=None):
    with open(path or EXE, 'rb') as f:
        return f.read()


def symbols(d):
    anchor = d.find(b'Print_Display_\x14\x18\x11\x00')
    if anchor < 0:
        raise SystemExit('symbol anchor not found')
    # walk backwards to the first record of the blob
    start = anchor + 14
    while True:
        prev = start
        # a record ends right before `start`; find its beginning by scanning back
        # for a plausible header 10 bytes before a name of the right length
        found = None
        for back in range(11, 80):
            i = start - back
            if i < 0:
                break
            addr, a, b, kind, ln = struct.unpack_from('<IHHBB', d, i)
            if ln == back - 10 and 0x1000 <= addr < 0x200000 and a == 1 and kind in (3, 4, 5, 6):
                nm = d[i + 10:i + 10 + ln]
                if re.fullmatch(rb'[\w@$.]+', nm):
                    found = i
                    break
        if found is None:
            break
        start = found
        if start == prev:
            break
    out, i = [], start
    while i + 10 < len(d):
        addr, a, b, kind, ln = struct.unpack_from('<IHHBB', d, i)
        if ln == 0 or i + 10 + ln > len(d):
            break
        nm = d[i + 10:i + 10 + ln]
        if not re.fullmatch(rb'[\w@$.]+', nm):
            break
        out.append((addr, nm.decode()))
        i += 10 + ln
    return out


def dis(d, lin, n=200, out=print):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    off = lin + DELTA
    for i in md.disasm(d[off:off + n], lin):
        out('  %08x %-8s %s' % (i.address, i.mnemonic, i.op_str))


if __name__ == '__main__':
    d = load()
    s = symbols(d)
    print('symbols:', len(s), file=sys.stderr)
    pat = sys.argv[1] if len(sys.argv) > 1 else '.'
    for a, nm in s:
        if re.search(pat, nm):
            print('%08x  %s' % (a, nm))
