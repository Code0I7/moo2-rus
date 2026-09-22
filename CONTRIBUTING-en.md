# Contributing

[Русский](CONTRIBUTING.md) | **English**

## Report a problem

A screenshot is the most useful contribution. Open an
[issue](../../issues/new/choose) and pick "Ошибка в тексте" (text bug) or
"Предложение по переводу" (translation suggestion).

## Fix the translation

1. Put a clone of the repository inside the game folder
   (`<game>/moo2-rus`) and install Python 3.8+.
2. `python make.py build` — extracts the English text from the game into
   `text/` and builds the translation.
3. Find the entry: `python tools/show.py HELP` lists ids, limits and text.
4. Fix the line in `tr/<FILE>*.jsonl` (or `python tools/settr.py <FILE> fix.jsonl`).
5. `python make.py install` and check in the game.
6. `python make.py check` — expect 0 lost markers, 0 missing strings and
   0 overflowing texts.

Rules: terms are the same everywhere (`tools/terms.py`), abbreviations only
where nothing else fits ([list](docs/ABBREVIATIONS.md), in Russian), never
drop substitution markers (invisible bytes 0x80–0x95). Details are in the
[technical documentation](docs/DEVELOPMENT-en.md).

## Pull requests

- one fix per PR
- describe the fix and add a before/after screenshot if on-screen text changed;
- never add game files (`*.LBX`, `*.EXE`, the contents of `text/` or `backup/`).
