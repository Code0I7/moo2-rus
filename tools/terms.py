# -*- coding: utf-8 -*-
"""Terminology check: the same game term must read the same everywhere.

Each rule pairs an English pattern with the Russian stem that has to show up
whenever the English one does, plus stems that must never be used for it.
Russian is inflected, so the Russian side is a regex over word stems.

    python terms.py            # every rule
    python terms.py freighter  # only rules whose name contains the word
"""
import sys, os, re, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import PROJ, ROOT
TEXT = os.path.join(PROJ, 'text')

# name: (english regex, russian regex that must match, russian regex that must not)
RULES = {
    'food':         (r'\bfood\b', r'пищ|голод|урожа', r'(?<![а-яё])[еЕ]д[аыеуой](?![а-яё])'),
    'freighter':    (r'\bfreighters?\b', r'грузовоз', r'транспорт'),
    'transport':    (r'\btransports?\b(?! ?ship)(?! food| colonists)', r'транспорт|перевоз|телепорт',
                     r'грузовоз'),
    'colony ship':  (r'\bcolony ships?\b', r'колонизатор', r'колониальн\w* корабл'),
    'outpost ship': (r'\boutpost ships?\b', r'аванп', None),
    'colony base':  (r'\bcolony bases?\b', r'колониальн\w* баз', None),
    'star base':    (r'\bstar ?bases?\b', r'звёздн\w* баз', None),
    'battlestation': (r'\bbattle ?stations?\b', r'боев\w* станц', None),
    'star fortress': (r'\bstar fortress', r'крепост', r'орбитальн\w* крепост'),
    'command points': (r'\bcommand points?\b', r'командн\w* очк', None),
    'command rating': (r'\bcommand rating', r'командован', None),
    'beam attack':  (r'\bbeam attack', r'лучев\w* (атак|оруж)', r'атака лучом'),
    'beam defense': (r'\bbeam defen[cs]e', r'защит\w* от луч', None),
    'missile evasion': (r'\bmissile evasion', r'уклон\w*\.?( \w+){0,2} от ракет', None),
    'point defense': (r'\bpoint defen[cs]e', r'точечн\w* оборон', r'\bПРО\b'),
    'heavy mount':  (r'\bheavy mount', r'тяжёл\w* установк', None),
    'research points': (r'\bresearch points?\b|\bRPs?\b', r'очк\w*\.? наук|\bОН\b', None),
    'BC':           (r'\bBC\b|\bBC\'?s\b', r'\bКР\b|кредит|купить|доход', r'\bБК\b'),
    'marines':      (r'\bmarines?\b', r'десант', r'морпех|морск\w* пехот'),
    'morale':       (r'\bmorale\b', r'морал', None),
    'pollution':    (r'\bpollution\b', r'загрязн', None),
    'feudal':       (r'\bfeudal', r'феодал', None),
    'dictatorship': (r'\bdictatorship', r'диктатур', None),
    'democracy':    (r'\bdemocrac', r'демократ', None),
    'unification':  (r'\bunification\b', r'унификац', None),
    'confederation': (r'\bconfederation', r'конфедерац', None),
    'imperium':     (r'\bimperium\b', r'импер', None),
    'federation':   (r'(?<!con)federation', r'федерац', None),
    'terran':       (r'\bterran\b', r'земн|земл', r'земноподоб|терран'),
    'arid':         (r'\barid\b', r'засушлив', r'\bсух'),
    'swamp':        (r'\bswamp', r'болот', None),
    'ocean':        (r'\bocean', r'океан', None),
    'tundra':       (r'\btundra', r'тундр', None),
    'desert':       (r'\bdesert\b', r'пустын', None),
    'barren':       (r'\bbarren\b', r'бесплод', None),
    'toxic':        (r'\btoxic\b(?! waste| amoeb| and polluting)', r'токсич', None),
    'radiated':     (r'\bradiated\b', r'радиоактив', None),
    'gaia':         (r'\bgaia\b', r'\bге[яиюе]', None),
    'low g':        (r'\blow[- ]g\b|\blow gravity', r'низк\w* (g|гравитац)', r'слаб\w* (g|гравитац)'),
    'heavy g':      (r'\b(heavy|high)[- ]g\b|\b(heavy|high) gravity', r'высок\w* (g|гравитац)|тяжёл\w* (g|гравитац)', None),
    'ultra rich':   (r'\bultra[- ]rich', r'сверхбогат', r'оч\. богат'),
    'ultra poor':   (r'\bultra[- ]poor', r'сверхбедн', r'оч\. бедн'),
    'abundant':     (r'\babundant\b', r'обил', None),
    'antarans':     (r'\bantaran', r'антаран', None),
    'guardian':     (r'\bguardian\b', r'страж', None),
    # the game's own title stays in Latin letters
    'orion':        (r'(?<!master of )(?<!play )\borion\b(?!\s*(ii|\]\[))', r'орион', None),
    'leader':       (r'\bleaders?\b',
                     r'лидер|офицер|правител|вожд|аграри|финансист|бригадир|импер|началом|власт|глав',
                     None),
    'spy':          (r'\bsp(y|ies)\b', r'шпион|агент', None),
    'population':   (r'\bpopulation\b', r'населени|колонист|жител|рождаем|единиц', None),
    'freighter fleet': (r'\bfreighter fleet', r'грузовоз', None),
    'trade goods':  (r'\btrade goods\b', r'товар', None),
    'housing':      (r'\bhousing\b', r'жиль', None),
    'research lab': (r'\bresearch lab', r'научн\w* лаборатор', r'исследовательск\w* лаборатор'),
    'robotic factory': (r'\brobotic factor', r'робозавод', r'роботизирован'),
    'pollution processor': (r'\bpollution processor', r'переработчик\w* отход', r'очистн'),
    'atmosphere renewer': (r'\batmospher\w* renewer', r'обновител\w* атмосфер', None),
    'radiation shield': (r'\bradiation shield', r'радиационн\w* щит', r'противорадиац'),
    'flux shield':  (r'\bflux shield', r'флюкс', None),
    'barrier shield': (r'\bbarrier shield', r'барьерн\w* щит', None),
    'missile base': (r'\bmissile base', r'ракетн\w* баз', None),
    'ground batteries': (r'\bground batter', r'наземн\w* батаре', None),
    'fighter garrison': (r'\bfighter garrison', r'гарнизон', None),
    'marine barracks': (r'\bmarine barracks', r'казарм\w* десант', None),
    'armor barracks': (r'\barmou?r barracks', r'казарм\w* бронетехник', None),
    'space academy': (r'\bspace academy', r'космическ\w* академ', None),
    'spaceport':    (r'\bspaceport', r'космопорт', None),
    'star gate':    (r'\bstar ?gate', r'звёздн\w* врат', None),
    'dimensional portal': (r'\bdimensional portal', r'портал\w* измерени', r'пространственн\w* портал'),
    'stellar converter': (r'\bstellar converter', r'звёздн\w* конвертер', None),
    'troop pods':   (r'\btroop pods?\b', r'десантн\w* отсек', None),
    'reinforced hull': (r'\breinforced hull', r'усиленн\w* корпус', None),
    'tractor beam': (r'\btractor beam', r'тягов\w* луч', None),
    'transporters': (r'\btransporters?\b', r'транспортер', None),
    'assault shuttle': (r'\bassault shuttle', r'штурмов\w* шаттл', None),
    'doom star':    (r'\bdoom ?stars?\b', r'зв[её]зд\w* смерти', None),
    'titan':        (r'\btitans?\b', r'титан', None),
    'battleship':   (r'\bbattleships?\b', r'линкор', None),
    'cruiser':      (r'\bcruisers?\b', r'крейсер', None),
    'destroyer':    (r'\bdestroyers?\b', r'эсминц|эсминец', None),
    'frigate':      (r'\bfrigates?\b', r'фрегат', None),
    'interceptor':  (r'\binterceptors?\b', r'перехватчик', None),
    'bomber':       (r'\bbombers?\b', r'бомбардировщик', None),
    'cloaking':     (r'\bcloaking device', r'маскировк', r'маскировочн\w* устройств'),
    'ecm jammer':   (r'\becm jammer', r'глушител', None),
    'eccm':         (r'\bECCM\b', r'ПРЭБ', r'ЭККМ'),
    'stealth field': (r'\bstealth field', r'пол\w* невидимост', None),
    'anti-matter':  (r'\banti-?matter\b', r'антимат|аннигиляц', r'антиматериальн'),
    'hyperspace communications': (r'\bhyperspace communication', r'гиперсвяз', None),
    'subspace communications': (r'\bsub-?space communication', r'подпростр', None),
    'research':     (r'\bresearch\b', r'наук|научн|исследов|учён|ОН\b|лаборатор|разработ', None),
}


def load():
    out = []
    for jf in sorted(glob.glob(os.path.join(TEXT, '*.json'))):
        d = json.load(open(jf, encoding='utf-8'))
        seen = set()
        group = 6 if d['file'] in ('TECHNAME.LBX', 'KENTEXT.LBX', 'KENTEXT1.LBX', 'JIMTEXT.LBX',
                                   'JIMTEXT2.LBX', 'BILLTEXT.LBX', 'BILLTEX2.LBX') else 1
        for e in d['entries']:
            ru = e.get('ru')
            if not ru:
                continue
            it = e['id'].split('/')[0]
            if group > 1 and int(it) % group:
                continue            # language copies of the same entry
            key = (e['en'], ru)
            if key in seen:
                continue
            seen.add(key)
            out.append((d['file'], e['id'], e['en'], ru))
    return out


def check(only=None):
    rows = load()
    bad = []
    for name, (en_rx, ru_ok, ru_bad) in RULES.items():
        if only and only not in name:
            continue
        er = re.compile(en_rx, re.I)
        ok = re.compile(ru_ok, re.I)
        nb = re.compile(ru_bad, re.I) if ru_bad else None
        for f, i, en, ru in rows:
            if not er.search(en):
                continue
            miss = not ok.search(ru)
            wrong = nb.search(ru) if nb else None
            if miss or wrong:
                bad.append((name, f, i, 'MISSING' if miss else 'WRONG: ' + wrong.group(0), en, ru))
    return bad


if __name__ == '__main__':
    only = sys.argv[1] if len(sys.argv) > 1 else None
    bad = check(only)
    for name, f, i, why, en, ru in bad:
        print('[%s] %s %s  %s\n    EN: %s\n    RU: %s' % (name, f, i, why, en.replace('\n', ' ')[:300],
                                                      ru.replace('\n', ' ')[:300]))
    print('%d problems' % len(bad))
