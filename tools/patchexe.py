# -*- coding: utf-8 -*-
"""Patch ORION150.EXE for Cyrillic, and translate the strings compiled into it.

Separate problems, each documented at its own table below:

  SITES    two drawing routines refuse character codes over 0x80
  WIDEN    two more read the glyph offset as a signed 16 bit number
  FULL256  the font tables are copied for characters 0..254, never 255 (я)
  STRINGS  a couple of format strings live in the data segment
  POOL     strings the 1.50 patch prints itself (New Game labels, units, race
           pick labels, fleet messages) plus a few same-length data strings

Linear address -> file offset is addr + 0x9569E (see syms.py); POOL and
STRINGS use plain file offsets because they sit in the appended patch module.
Everything here is reversible: `python patchexe.py revert`.
"""
import sys, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
EXE = os.path.join(ROOT, 'ORION150.EXE')
BAK = os.path.join(PROJ, 'backup', 'ORION150.EXE.orig')
DELTA = 0x9569E

OLD = b'\x3d\x80\x00\x00\x00'      # cmp eax, 0x80
NEW = b'\x3d\x00\x01\x00\x00'      # cmp eax, 0x100
SITES = [(0x112629, 'Print_Clipped_Character_'),
         (0x11308c, 'Print_Character_To_Bitmap_')]

# Print_Clipped_Letter_ and its bitmap twin keep the glyph offset in a local
# and then index the glyph blob with `movsx reg, word [local]` - as a *signed*
# 16 bit number.  Print_Character_ reads the same value as a plain dword.  The
# shipped font stays under 32K so nobody ever noticed, but Cyrillic pushes the
# larger faces past 0x8000, the offset goes negative, and these two routines
# decode whatever byte lands under the resulting pointer: the unreadable smear
# over the picture in INFO -> Tech Review and over every cell of Race
# Statistics.
#
# Reading it unsigned is enough as long as the glyph area stays under 64K,
# which is why moo2font.build() makes identical glyphs share their bytes; the
# word-sized *load* of the offset itself (at 0x11282e / 0x11322f) is therefore
# left alone.  Each replacement is exactly as long as the original - a trailing
# nop takes up the slack - so every relative jump still lands where it did.
_PTRD16 = bytes.fromhex('0fbf55e8')          # movsx edx, word [ebp-0x18]
_PTRD32 = bytes.fromhex('8b55e890')          # mov   edx, dword [ebp-0x18] ; nop
_PTRA16 = bytes.fromhex('0fbf45e8')          # movsx eax, word [ebp-0x18]
_PTRA32 = bytes.fromhex('8b45e890')          # mov   eax, dword [ebp-0x18] ; nop
WIDEN = [
    (0x112861, _PTRD16, _PTRD32, 'Print_Clipped_Letter_ ptr 1'),
    (0x1128c5, _PTRD16, _PTRD32, 'Print_Clipped_Letter_ ptr 2'),
    (0x11292a, _PTRA16, _PTRA32, 'Print_Clipped_Letter_ ptr 3'),
    (0x113262, _PTRD16, _PTRD32, 'Print_Clipped_Letter_To_Bitmap_ ptr 1'),
    (0x1132c6, _PTRD16, _PTRD32, 'Print_Clipped_Letter_To_Bitmap_ ptr 2'),
    (0x113337, _PTRA16, _PTRA32, 'Print_Clipped_Letter_To_Bitmap_ ptr 3'),
]
# glyph area must stay below this or the word sized offset load truncates
GLYPH_AREA_LIMIT = 0x10000

# Set_Font_ and friends copy the per character width and glyph offset tables
# into the engine's working arrays with `for (i = 0; i < 0xff; i++)`, so index
# 255 is never written and keeps whatever the data segment happened to hold.
# In CP1251 255 is lowercase я, which therefore drew a glyph from some other
# font (the letter that looked too small or too big) and, once the offset is
# read as a full dword, dereferenced garbage and killed the game.
_LOOP254 = bytes.fromhex('817dfcff000000')   # cmp dword [ebp-4], 0xff
_LOOP255 = bytes.fromhex('817dfc00010000')   # cmp dword [ebp-4], 0x100
FULL256 = [
    (0x1107d0, 'Set_Font_ copies char 255'),
    (0x1108e1, 'Set_Font_Solid_ copies char 255'),
    (0x110a34, 'Set_Remap_Font_Style_ copies char 255'),
]

# hard coded format strings in the data segment; replacements must be exactly
# as long as the original (cp1251), the string table has no room to grow
STRINGS = [
    (0x1f79a8, b'%s (%d EP)', '%s (%d ОО)', 'experience points suffix'),
]

# The 1.50 patch keeps the New Game screen's galaxy size, player count and
# starting tech level in its own string pool, appended after the LE image.
# The literals are packed one after another and each is referenced by its own
# address, so a replacement may be shorter (the rest is filled with NUL) but
# never longer - hence the abbreviations.  Offsets are plain file offsets.
POOL = [
    (0x337a37, b'Pre-warp', 'Доварп.'),
    (0x337a40, b'Average', 'Средний'),
    (0x337a48, b'Post-warp', 'Постварп.'),
    (0x337a52, b'Advanced', 'Развитый'),
    (0x337ae4, b'2 Players', '2 игрока'),
    (0x337aee, b'3 Players', '3 игрока'),
    (0x337af8, b'4 Players', '4 игрока'),
    (0x337b02, b'5 Players', '5 игроков'),
    (0x337b0c, b'6 Players', '6 игроков'),
    (0x337b16, b'7 Players', '7 игроков'),
    (0x337b20, b'8 Players', '8 игроков'),
    (0x337b2a, b'Random', 'Случ.'),
    (0x337c82, b'Small', 'Малая'),
    (0x337c88, b'Medium', 'Средн.'),
    (0x337c8f, b'Large', 'Круп.'),
    (0x337c95, b'Cluster', 'Скопл.'),
    (0x337c9d, b'Huge', 'Огр.'),
    # units and the few labels the patch prints itself
    (0x32e4ef, b' BC', ' КР'),
    (0x32e4f3, b'Food per farmer', 'Пища на фермера'),
    (0x32e50f, b'Food', 'Пища'),
    (0x32e51d, b'Base food per', 'Базовая пища'),
    (0x32e52b, b'Absorber Overloaded', 'Поглотитель перегр.'),
    (0x1f7bc0, b'BC', 'КР'),
    (0x1f89eb, b'RP', 'ОН'),
    (0x1f89ee, b'BC', 'КР'),
    (0x1f89f1, b'FP', 'ЕД'),
    (0x1f8a60, b'%i RP', '%i ОН'),          # research screen field costs
    (0x1f8a66, b'%i FP', '%i ЕД'),
    (0x1f8a6c, b'%i PR', '%i ПР'),
    (0x1f8a72, b' RP', ' ОН'),
    (0x1f8a76, b' FP', ' ЕД'),
    (0x1f8a7a, b' PR', ' ПР'),
    (0x1f7e68, b'RP', 'ОН'),
    (0x1f7e6b, b'FP', 'ЕД'),
    (0x1f7e6e, b'PR', 'ПР'),
    (0x1f89f7, b'PR', 'ПР'),                # race report
    (0x1f7ac7, b'Orion', 'Орион'),          # the Orion star, named by the map
    (0x1f7c0b, b'Orion', 'Орион'),          # generator (new games only)
    (0x1f713c, b'  %d BC', '  %d КР'),      # diplomacy offers
    (0x1f71ab, b'%d BC', '%d КР'),
    (0x1f8970, b'1 BC', '1 КР'),            # custom race money picks
    (0x1f8975, b'0.5 BC', '0.5 КР'),
    # Custom race screen: 1.50 builds the pick labels ("-50% Growth") from
    # these templates, one per game language; all five get the Russian so the
    # choice of language.ini does not matter.  Label first reads better in
    # Russian and keeps the numbers lined up above the dotted leaders.
    (0x337d10, b'$V$% Growth', 'Рост $V$%'),
    (0x337d1c, b'$V$% Zuwachs', 'Рост $V$%'),
    (0x337d29, b'Croissance ($V$%)', 'Рост $V$%'),
    (0x337d3b, b'$V$% Crecimiento', 'Рост $V$%'),
    (0x337d4c, b'Crescita $V$%', 'Рост $V$%'),
    (0x337d5a, b'$V$ Food', 'Пища $V$'),
    (0x337d63, b'$V$ Nahrung', 'Пища $V$'),
    (0x337d6f, b'$V$ Nourriture', 'Пища $V$'),
    (0x337d7e, b'$V$ Alimentos', 'Пища $V$'),
    (0x337d8c, b'Cibo $V$', 'Пища $V$'),
    (0x337d95, b'$V$ Production', 'Произв. $V$'),
    (0x337da4, b'$V$ Produktion', 'Произв. $V$'),
    (0x337db3, b'$V$ Produccio}n', 'Произв. $V$'),
    (0x337dc3, b'Produzione $V$', 'Произв. $V$'),
    (0x337dd2, b'$V$ Research', 'Наука $V$'),
    (0x337ddf, b'$V$ Forschung', 'Наука $V$'),
    (0x337ded, b'$V$ Recherche', 'Наука $V$'),
    (0x337dfb, b'$V$ Investigacio}n', 'Наука $V$'),
    (0x337e0e, b'Ricerca $V$', 'Наука $V$'),
    (0x337e1a, b'$V$ BC', 'КР $V$'),
    (0x337e21, b'$V$ MC', 'КР $V$'),
    # product names the patch prints itself - kept identical to ESTRINGS, in
    # case it ever compares them with the names the base game uses
    (0x32e548, b'Trade Goods', 'Товары'),
    (0x32e554, b'Housing', 'Жильё'),
    (0x32e78a, b'Animation speed $SIGN$$VAL$', 'Анимация $SIGN$$VAL$'),
    (0x32ef50, b'^ Repeat ^', '^ Повтор ^'),
    # combat and fleet messages added by 1.50
    (0x337e34, b'Damper field prevents the use of transporters.',
     'Гасящее поле не даёт применить транспортеры.'),
    (0x337e64, b'Ships trapped in a black hole may not be boarded.',
     'Корабль в чёрной дыре нельзя взять на абордаж.'),
    (0x337e98, b'Ships trapped in a black hole may not board.',
     'Из чёрной дыры нельзя идти на абордаж.'),
    (0x337ec8, b'Phased out ships may not be boarded.',
     'Абордаж корабля вне фазы невозможен.'),
    (0x337ef0, b'This game does not need augmented engines fixup.',
     'Правка усиленных двигателей не нужна.'),
    (0x337f24, b'Augmented engines fixup applied. All ships and designs created in '
               b'1.50.2 have normal speed now.',
     'Правка усиленных двигателей применена: корабли и проекты 1.50.2 снова '
     'с обычной скоростью.'),
    (0x339c68, b'Departure of the fleet routed past a black hole was cancelled due to '
               b'removal of its navigator.',
     'Вылет флота мимо чёрной дыры отменён: у него больше нет навигатора.'),
    (0x339cc8, b'ETA of the fleet without navigator increased by $D$ turn$S$.',
     'Флот без навигатора прибудет позже, ходов: $D$.'),
    (0x339d08, b'The fleet on course to pass the black hole will have no navigator. If '
               b'this is not remedied the fleet will be lost at the end of the turn. '
               b'Continue?',
     'Флот, идущий мимо чёрной дыры, останется без навигатора. Если это не '
     'исправить, к концу хода флот погибнет. Продолжить?'),
    (0x339d9c, b'The fleet without navigator will be delayed by $D$ turn$S$. Continue?',
     'Флот без навигатора задержится, ходов: $D$. Продолжить?'),
]


def patch(revert=False):
    if not os.path.exists(BAK):
        os.makedirs(os.path.dirname(BAK), exist_ok=True)
        shutil.copyfile(EXE, BAK)
        print('backup ->', os.path.relpath(BAK, ROOT))
    data = bytearray(open(EXE, 'rb').read())
    want, put = (NEW, OLD) if revert else (OLD, NEW)
    done = 0
    for lin, name in SITES:
        off = lin + DELTA
        cur = bytes(data[off:off + 5])
        if cur == put:
            print('  %-28s %08x already done' % (name, lin))
            continue
        if cur != want:
            raise SystemExit('  %s: unexpected bytes %s at %08x' % (name, cur.hex(), lin))
        data[off:off + 5] = put
        done += 1
        print('  %-28s %08x  %s -> %s' % (name, lin, cur.hex(), put.hex()))
    for off, orig, ru in POOL:
        new = ru.encode('cp1251')
        if len(new) > len(orig):
            raise SystemExit('  %r: %d bytes, at most %d' % (ru, len(new), len(orig)))
        new += b'\x00' * (len(orig) - len(new))
        want, put = (new, orig) if revert else (orig, new)
        cur = bytes(data[off:off + len(orig)])
        if cur == put:
            continue
        if cur != want:
            raise SystemExit('  pool %r: unexpected bytes %r at %08x' % (ru, cur, off))
        data[off:off + len(orig)] = put
        done += 1
    print('  %-44s %d strings' % ('1.50 patch / data segment strings', len(POOL)))
    for lin, what in FULL256:
        off = lin + DELTA
        want, put = (_LOOP255, _LOOP254) if revert else (_LOOP254, _LOOP255)
        cur = bytes(data[off:off + len(_LOOP254)])
        if cur == put:
            print('  %-44s %08x already done' % (what, lin))
            continue
        if cur != want:
            raise SystemExit('  %s: unexpected bytes %s at %08x' % (what, cur.hex(), lin))
        data[off:off + len(_LOOP254)] = put
        done += 1
        print('  %-44s %08x  %s -> %s' % (what, lin, cur.hex(), put.hex()))
    for lin, orig, wide, what in WIDEN:
        off = lin + DELTA
        want, put = (wide, orig) if revert else (orig, wide)
        cur = bytes(data[off:off + len(orig)])
        if cur == put:
            print('  %-44s %08x already done' % (what, lin))
            continue
        if cur != want:
            raise SystemExit('  %s: unexpected bytes %s at %08x' % (what, cur.hex(), lin))
        data[off:off + len(orig)] = put
        done += 1
        print('  %-44s %08x  %s -> %s' % (what, lin, cur.hex(), put.hex()))
    for off, old, ru, what in STRINGS:
        new = ru.encode('cp1251')
        if len(new) != len(old):
            raise SystemExit('  %s: %d bytes, must be %d' % (what, len(new), len(old)))
        want, put = (new, old) if revert else (old, new)
        cur = bytes(data[off:off + len(old)])
        if cur == put:
            print('  %-28s %08x already done' % (what, off))
            continue
        if cur != want:
            raise SystemExit('  %s: unexpected bytes %r at %08x' % (what, cur, off))
        data[off:off + len(old)] = put
        done += 1
        print('  %-28s %08x  %r -> %r' % (what, off, want, put))
    if done:
        open(EXE, 'wb').write(bytes(data))
    print('%s: %d site(s) changed' % ('revert' if revert else 'patch', done))


if __name__ == '__main__':
    patch(revert=len(sys.argv) > 1 and sys.argv[1] == 'revert')
