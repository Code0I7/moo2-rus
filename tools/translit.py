# -*- coding: utf-8 -*-
"""Transliterate the game's proper names (stars, ships, rulers, heroes).

Generates tr/<FILE>.auto.jsonl for the name-only entries so they render in
the same alphabet as the rest of the interface.
"""
import sys, os, json, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT

ROMAN = re.compile(r'^(?=[IVXLC])I{0,3}[VX]?I{0,3}$')

# results the rules get wrong or make unfortunate
OVERRIDE = {
    'Kher': 'Кхер', 'Hawk': 'Хок', 'Draxx': 'Дракс', 'Emo': 'Эмо',
    'Aquasarrious': 'Аквасариус', 'Ruola': 'Руола', 'Slith': 'Слиз',
    'Cyr': 'Кир', 'Sol': 'Сол', 'Ursa': 'Урса',
    # ruler and leader names that are ordinary English words
    'Fireblade': 'Файрблейд', 'Greywind': 'Грейвинд', 'Greymoran': 'Греймморан',
    'Vale': 'Вейл', 'Laurel': 'Лорел', 'Morfane': 'Морфейн', 'Ariel': 'Ариэль',
    'Alexander': 'Александр', 'Caesar': 'Цезарь', 'Reid': 'Рид',
    'Strader': 'Страйдер', 'Razor': 'Рейзор', 'Black': 'Блэк',
    'Mystic': 'Мистик', 'Matrix': 'Матрикс', 'Claw': 'Клоу', 'Sparky': 'Спарки',
    'Ralleia': 'Раллея', 'Nile': 'Нил', 'Brainac': 'Брейниак',
    'Crystous': 'Кристус', 'Primus': 'Примус', 'Maximus': 'Максимус',
    'Cog': 'Ког', 'Geode': 'Геод', 'Krakatoa': 'Кракатау', 'Sauron': 'Саурон',
    # star name fragments whose slot is only 3 to 5 bytes wide
    'Pax': 'Пас', 'Vij': 'Виж', 'Vox': 'Вок', 'Aji': 'Ажи', 'Jabo': 'Жабо',
    'Jobe': 'Жобе', 'Juza': 'Жуза', 'Exis': 'Экси', 'Linx': 'Линк',
    'Gadjo': 'Гаджо', 'Justa': 'Жуста', 'Xenon': 'Зенон',
}
from shipwords import WORDS as SHIP_WORDS       # noqa: E402

DIGRAPHS = [
    ('shch', 'щ'), ('sch', 'ш'), ('tch', 'ч'), ('ious', 'иус'),
    ('xx', 'кс'), ('ow', 'оу'), ('aw', 'о'), ('ew', 'ью'),
    ('sh', 'ш'), ('ch', 'ч'), ('ph', 'ф'), ('th', 'т'), ('zh', 'ж'), ('kh', 'х'),
    ('gh', 'г'), ('wh', 'в'), ('ck', 'к'), ('qu', 'кв'), ('x', 'кс'), ('j', 'дж'),
    ('yo', 'ё'), ('yu', 'ю'), ('ya', 'я'), ('ye', 'е'), ('yi', 'йи'),
    ('ee', 'и'), ('oo', 'у'), ('ou', 'у'), ('ea', 'и'), ('ie', 'и'), ('ai', 'ай'),
    ('ay', 'ей'), ('ey', 'ей'), ('oy', 'ой'), ('au', 'ау'), ('eu', 'ев'),
    ('ae', 'э'), ('oe', 'э'), ('ia', 'ия'), ('io', 'ио'), ('iu', 'иу'),
]
SINGLE = {'a': 'а', 'b': 'б', 'c': 'к', 'd': 'д', 'e': 'е', 'f': 'ф', 'g': 'г',
          'h': 'х', 'i': 'и', 'k': 'к', 'l': 'л', 'm': 'м', 'n': 'н', 'o': 'о',
          'p': 'п', 'q': 'к', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у', 'v': 'в',
          'w': 'в', 'y': 'и', 'z': 'з'}
VOWELS = set('aeiouy')


def _word(w):
    if w in SHIP_WORDS:
        return SHIP_WORDS[w]
    if w in OVERRIDE:
        return OVERRIDE[w]
    if len(w) > 1 and ROMAN.match(w):
        return w                      # Falcon II stays Falcon II
    low = w.lower()
    out, i = [], 0
    n = len(low)
    while i < n:
        ch = low[i]
        if ch == 'c' and i + 1 < n and low[i + 1] in 'eiy':
            out.append('с'); i += 1; continue
        if ch == 'y' and (i == 0 or low[i - 1] not in VOWELS) and i + 1 < n and low[i + 1] in VOWELS:
            # ya/ye/yu handled by digraphs; a bare leading y before a vowel is Й
            out.append('й'); i += 1; continue
        if ch == 'e' and i == 0:
            out.append('э'); i += 1; continue
        for d, r in DIGRAPHS:
            if low.startswith(d, i):
                out.append(r); i += len(d); break
        else:
            out.append(SINGLE.get(ch, ch))
            i += 1
    ru = ''.join(out)
    if w[:1].isupper():
        ru = ru[:1].upper() + ru[1:]
    return ru


def translit(s):
    return re.sub(r"[A-Za-z][A-Za-z']*", lambda m: _word(m.group()), s)


def gen(name, pick, out_name=None):
    """pick(entry) -> True for entries that are plain proper names"""
    path = os.path.join(PROJ, 'text', name + '.json')
    d = json.load(open(path, encoding='utf-8'))
    lines, skipped = [], 0
    for e in d['entries']:
        # the existing ru is ignored on purpose: this file is regenerated from
        # scratch every run and anything written by hand overrides it later
        if not pick(e):
            continue
        ru = translit(e['en'])
        if ru == e['en']:
            continue
        if e['cap'] and len(ru.encode('cp1251')) > e['cap']:
            skipped += 1
            continue
        lines.append(json.dumps([e['id'], ru], ensure_ascii=False))
    outp = os.path.join(PROJ, 'tr', (out_name or name) + '.auto.jsonl')
    open(outp, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('%-12s %5d names -> %s   (%d too long, left as is)' %
          (name, len(lines), os.path.basename(outp), skipped))


if __name__ == '__main__':
    # only the field at offset 0 of a record holds the name; anything after it
    # is leftover from a longer name the game once wrote into the same buffer
    def name(e):
        return (e['id'].split('/')[-1] == '0' and
                bool(re.fullmatch(r"[A-Za-z0-9 '\-\.]+", e['en'])))
    gen('RACENAME', name)
    gen('STARNAME', name)
    gen('SHIPNAME', name)
    gen('HERODATA', name)
