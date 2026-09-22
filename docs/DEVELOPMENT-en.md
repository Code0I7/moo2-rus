# Technical documentation

[Русский](DEVELOPMENT.md) | **English**

How the Russian translation of Master of Orion II for patch 1.50.26 works:
data formats, the engine bugs we ran into and how they are worked around, and
the build pipeline.

- [Overview](#overview)
- [Repository layout](#repository-layout)
- [Build pipeline](#build-pipeline)
- [ORION150.EXE patches](#orion150exe-patches)
- [Fonts](#fonts)
- [Data constraints](#data-constraints)
- [Text box sizes](#text-box-sizes)
- [Workflow](#workflow)
- [Translation conventions](#translation-conventions)
- [Release build](#release-build)
- [Not done yet](#not-done-yet)

## Overview

The translation installs as a 1.50 mod (`150/mods/rus`, config `RUS.CFG`) plus:

- 12 LBX files in the game folder that the patch offers no config parameter
  for (the originals are kept in `backup/root/`);
- a reversible patch of `ORION150.EXE` (original in `backup/ORION150.EXE.orig`).

The repository contains no game files. `make.py` extracts the English text
from the installed game into `text/`, applies the translation from `tr/` and
builds the Russian LBX files from the same original files. The pipeline is
reproducible: rebuilding produces byte-identical output.

The target core mod is **1.50 improved**: it ships its own English `HELP`,
`TECHDESC`, `HERODATA` and `KENTEXT` (changed numbers, no stale race pick
costs), so `dump_all.py` reads those from `150/mods/150i/lbx/`.

## Repository layout

| Path | Contents |
|---|---|
| `make.py` | entry point: `install`, `uninstall`, `build`, `check` |
| `tr/*.jsonl` | the translation: one `["<entry id>", "<Russian text>"]` per line |
| `cfg/EXTRA.CFG` | interface strings printed by the 1.50 patch itself (UTF-8, written as CP1251 on install) |
| `tools/` | tools (below) |
| `docs/` | documentation, abbreviations, changelog |
| `backup/`, `text/`, `work/` | local only, git-ignored |

| Tool | Purpose |
|---|---|
| `lbx.py`, `lbxtext.py` | LBX container; string extraction and injection (`fields`, `pool`, `rawpool` modes) |
| `dump_all.py` | English text from the game → `text/*.json` |
| `apply_tr.py` | `tr/` → `text/`, copies across language sub-files |
| `build.py` | builds the Russian LBX files into `150/mods/rus/lbx` |
| `install.py` | install: mod config, root files, enabling the mod |
| `mkcyr.py`, `moo2font.py` | generates Cyrillic in every font of `FONTS.LBX`/`IFONTS.LBX` |
| `patchexe.py` | `ORION150.EXE` patches |
| `markers.py` | substitution marker check |
| `verify.py` | checks that every translated string is present in the built file |
| `terms.py` | consistent terminology |
| `wrap.py`, `width.py`, `fitcheck.py` | width and line-wrap measurement from the font metrics |
| `translit.py`, `shipwords.py` | transliteration of star, ship and ruler names |
| `settr.py` | replaces an entry's translation in whichever `tr/` file holds it |
| `syms.py` | `ORION150.EXE` symbol table and disassembly helper (capstone) |
| `lbximg.py`, `imgprev.py`, `preview_font.py` | LBX picture codec, previews |
| `run.ps1`, `click.ps1`, `shot.ps1`, `send.ps1`, `dbx.py` | test automation: start DOSBox, click and capture the window without stealing focus |

## Build pipeline

```
dump_all.py → text/*.json (en) → apply_tr.py (+ tr/*.jsonl) → text/*.json (en+ru)
mkcyr.py → FONTS.LBX, IFONTS.LBX
build.py → 150/mods/rus/lbx/*.LBX
install.py → RUS.CFG, cfg/EXTRA.CFG, 12 root LBX files, enable RUS
patchexe.py → ORION150.EXE
verify.py, markers.py → checks
```

Translation files for one LBX load in this order, the last one wins:
`<FILE>.auto.jsonl` (transliteration), `<FILE>.jsonl`, `<FILE>.N.jsonl`,
`<FILE>.fix.jsonl`. Multi-language files (`TECHNAME`, `KENTEXT`, `JIMTEXT`,
`COUNCMSG`, …) keep a copy of each string per game language; the English one
is translated and copied over the rest (`FANOUT`, `GROUP_FANOUT`,
`BLOCK_FANOUT`, `SUB_FANOUT` in `apply_tr.py`), so the game shows Russian
whatever `language.ini` says.

## ORION150.EXE patches

All in `tools/patchexe.py`, reversible (`patchexe.py revert`). Linear address
→ file offset is `addr + 0x9569E`. The 1.50 patch module is appended after
the LE image and addressed by file offset. Function names come from the
symbol table the 1.50 patch left in the EXE (`tools/syms.py`).

| # | Where | Problem | Patch |
|---|---|---|---|
| 1 | `Print_Clipped_Character_` 0x112629, `Print_Character_To_Bitmap_` 0x11308c | `cmp eax,0x80`: codes above 0x7F are silently skipped — Cyrillic takes up space but draws nothing | `cmp eax,0x100` |
| 2 | `Print_Clipped_Letter_` 0x112861/0x1128c5/0x11292a and its bitmap twin 0x113262/0x1132c6/0x113337 | the glyph offset is read as a **signed** 16-bit value (`movsx`); the Cyrillic fonts grow past 0x8000, the pointer goes negative, and garbage appears above the Tech Review picture and in Race Statistics | `mov reg, dword` + `nop` (same length). Widening the offset load itself (0x11282e/0x11322f) crashes the game, so the glyph area is kept under 64 KB instead (see [Fonts](#fonts)) |
| 3 | `Set_Font_` 0x1107d0, `Set_Font_Solid_` 0x1108e1, `Set_Remap_Font_Style_` 0x110a34 | font tables are copied with `i < 0xff`: character 255 (CP1251 "я") is never set up and borrows another font's glyph | bound `0x100` |
| 4 | data segment | formats and units (`%s (%d EP)`, `%d BC`, `RP`, the `Orion` star) | same-length or shorter strings |
| 5 | 1.50 module string pool | New Game labels, race pick templates (`$V$% Growth`), fleet messages | never longer than the original; the literals are packed back to back and each is addressed on its own, hence abbreviations such as `Огр.`, `Круп.` |

## Fonts

- Entry 0 of `FONTS.LBX`/`IFONTS.LBX`: 6 fonts; width tables at
  `0x059C + i*0x100`, glyph offset tables at `0x0B9C + i*0x400` (dword),
  heights at `0x056C`, glyph data from `0x239C`. Letter spacing is `SPACING`
  in `width.py`.
- A glyph carries no length: the engine decodes exactly `height` rows. So
  identical glyphs can share one copy — that is how `moo2font.build()` keeps
  the whole glyph area under 64 KB (patch 2), and `mkcyr.py` refuses to write
  a font that exceeds it.
- Cyrillic is generated from each font's own strokes (`mkcyr.py`); letters
  identical to Latin ones are copied. «», – and — are added too (0x96/0x97
  are empty in the original fonts, so every dash printed as nothing).
- Recipes are checked in all 12 fonts (`preview_font.py`): mistakes only show
  at the small sizes (л reading as п, ы as "оı", щ as ц, У as Y).

## Data constraints

- The 1.50 patch validates each LBX record size: the string pools (ESTRINGS
  21000 B, HESTRNGS 13521 B, RSTRING0 6500 B, MAINTEXT 14×600 B) **must not
  grow**; `build.py` reports OVERFLOW.
- In `fields` mode a string may extend up to the next non-zero byte of the
  record; leftovers after the NUL in name fields limit the length.
- Bytes 0x80–0x95 are substitution markers (ruler, race, number). They are
  invisible in prose and easy to lose; `markers.py` compares the sets, with
  allowed omissions (English articles and plural endings) in `DROPPABLE`. For
  the same reason "…" (0x85) cannot be used in the translation.
- Cross-file reuse of identical sentences only applies to text with at least
  three letters: one- and two-letter records are hot keys and data bytes, and
  overwriting them broke game data.
- `install.py` replaces files in the game folder, so `dump_all.py` and
  `build.py` read the originals from `backup/root/`, never the installed
  Russian copy; `verify.py` catches this class of bug.
- A save stores the resolved LBX paths of its config
  (`\150\mods\RUS\lbx\HELP.LBX` …) and will not load if a file is missing
  ("… could not be found", the game terminates). So `uninstall` keeps
  `150/mods/rus/lbx` filled with the original English files (plus a
  `README.TXT`) and removes `RUS.CFG`: the mod disappears from the Launcher
  and old saves open in English.
- The Launcher does not decode `mod_name`/`mod_desc` (it shows raw bytes), so
  they are ASCII; everything the game prints lives in `cfg/EXTRA.CFG` in
  CP1251, one folder down (the Launcher treats any `*.CFG` in a mod folder as
  a mod).

## Text box sizes

The game renders at 640×480 and DOSBox only scales the frame, so pixel
budgets are absolute. Measured from screenshots (`wrap.py`, table `BOX`):

| Box | Font | Width | Lines |
|---|---|---|---|
| Tech Review: description | 2 | 174 px | 11 |
| Tech Review: list | 2 | 176 px | 1 |
| Tech Review: heading | 4 | 176 px, word ≤ 174 px (longer words are cut in the middle) | 2 |
| Reference: page | 4 | 384 px | 18 |
| Reference: "How to?" column | 3 | ~150 px | 1 |
| Planets: size column | 2 | ~60 px | 1 |

## Workflow

```bash
python make.py build                 # extract, apply the translation, build
python tools/show.py ESTRINGS        # a file's strings: id, limit, text
python tools/settr.py HELP fix.jsonl # replace entries' translation in place
python make.py install               # install into the game
python make.py check                 # markers, presence, terms, wrapping
```

Running the game for testing (config order matters):

```bash
DOSBOX/DOSBox.exe -conf 150/dosbox-150.conf -conf 150/dosbox.conf
```

`tools/run.ps1` does the same with `dosbox-test.conf` (`output=surface`: with
`ddraw`, SDL reads the mouse through DirectInput and ignores messages posted
to the window), then `click.ps1 -Game X Y` and `shot.ps1`, or `dbx.py`.

## Translation conventions

- CP1251; the game's control bytes (0x01–0x1F, 0x80–0x95, 0x9E) pass through
  untouched. `%s`, `%d`, `\n` keep their order.
- Terms are consistent across the whole translation (`terms.py`): грузовозы
  (freighters) vs транспорт (troop transport), пища (food), точечная оборона
  (point defense), climates as adjectives, Низкая/Обычная/Высокая G.
- Abbreviations only where nothing else fits; see
  [ABBREVIATIONS.md](ABBREVIATIONS.md) (in Russian).
- Proper names are transliterated (`translit.py` → `tr/*.auto.jsonl`, which
  is regenerated); manual fixes go into the regular `<FILE>.jsonl`.

## Release build

`.github/workflows/release.yml` runs on a `v*` tag: it builds `moo2-rus.exe`
(PyInstaller from `make.py`), packs it with `tr/` and `cfg/` into
`moo2-rus-<tag>.zip` and creates a draft release. The archive contains no
game files: the exe builds the translation from the user's own copy.

## Not done yet

- Buttons. The main panel is `BUFFER0.LBX`: labels
  are baked into frame 0, items 1–10 are the lit and pressed states. The
  picture codec is done (`lbximg.py`, lossless round trip on all 6489 game
  pictures); a programmatic label font did not reach the original's quality.
- The 1.50 hot key scripts (`150/scripts/main/MAIN*.LUA`) and the Mirror mod
  message.
- Mid- and late-game screens have only been spot-checked.
