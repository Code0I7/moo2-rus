# -*- coding: utf-8 -*-
"""Русификация Master of Orion II: установка, удаление, сборка, проверки.

    python make.py install     собрать перевод из файлов вашей игры и установить
    python make.py uninstall   вернуть оригинальные файлы и снять правку EXE
    python make.py build       только собрать (в 150/mods/rus/lbx), без установки
    python make.py check       проверки: маркеры, наличие строк, термины, переносы

Папка moo2-rus должна лежать прямо в папке игры (рядом с ORION150.EXE).
Из релиза то же самое делает moo2-rus.exe: без аргументов он спрашивает,
установить перевод или удалить.
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
from paths import PROJ, ROOT   # noqa: E402


def need_game():
    for f in ('ORION150.EXE', 'FONTS.LBX', 'HELP.LBX'):
        if not os.path.exists(os.path.join(ROOT, f)):
            raise SystemExit('Не найден %s в папке\n  %s\n\nРаспакуйте папку moo2-rus прямо в папку '
                             'игры (рядом с ORION150.EXE); нужен патч 1.50.26.' % (f, ROOT))


def step(title):
    print('\n== %s' % title)


def build():
    import dump_all, apply_tr, mkcyr, build as b
    step('Извлечение английского текста из файлов игры')
    dump_all.main()
    step('Перевод')
    apply_tr.main()
    step('Шрифты с кириллицей')
    mkcyr.main()
    step('Сборка LBX')
    b.main()


def install():
    need_game()
    build()
    import install as inst, patchexe
    step('Установка')
    inst.install()
    step('Правка ORION150.EXE')
    patchexe.patch()
    rc = check(quick=True)
    print('\nГотово. Запустите игру через Лаунчер: в разделе «Моды» должна стоять галочка «Russian».'
          if not rc else '\nУстановка завершилась с ошибками, см. выше.')
    return rc


def uninstall():
    need_game()
    import install as inst, patchexe
    inst.uninstall()
    patchexe.patch(revert=True)
    print('\nОригинальные файлы игры восстановлены.')


def check(quick=False):
    import markers, verify
    step('Маркеры подстановки')
    lost = markers.scan()
    print('потеряно маркеров: %d' % sum(len(v) for v in lost.values()))
    step('Все строки в собранных файлах')
    rc = verify.main()
    if quick:
        return rc
    import terms, wrap, json
    step('Единые термины (tools/terms.py)')
    print('расхождений: %d' % len(terms.check()))
    step('Переносы: описания в Обзоре технологий и страницы справочника')
    d = json.load(open(os.path.join(PROJ, 'text', 'HELP.json'), encoding='utf-8'))
    over = []
    for e in d['entries']:
        part = e['id'].split('/')
        if part[0] != '0' or part[2] != '103' or not e.get('ru'):
            continue
        n = int(part[1])
        if n < 211 and not wrap.fits(e['ru'], 'techreview'):
            over.append(('techreview', e['id']))
        elif 212 <= n <= 227 and not wrap.fits(e['ru'], 'reference'):
            over.append(('reference', e['id']))
    print('не помещаются: %d %s' % (len(over), over[:10]))
    return rc or (1 if lost or over else 0)


def menu():
    """double-clicked .exe: ask instead of printing usage"""
    print('Русификация Master of Orion II\n\n  1 - установить перевод\n  2 - удалить перевод\n')
    choice = input('Выберите 1 или 2 и нажмите Enter: ').strip()
    return {'1': 'install', '2': 'uninstall'}.get(choice, '')


def main():
    frozen = getattr(sys, 'frozen', False)
    cmd = sys.argv[1] if len(sys.argv) > 1 else (menu() if frozen else '')
    rc = 0
    try:
        if cmd == 'install':
            rc = install()
        elif cmd == 'uninstall':
            uninstall()
        elif cmd == 'build':
            need_game()
            build()
        elif cmd == 'check':
            rc = check()
        else:
            print(__doc__)
    except SystemExit as e:
        if e.code not in (None, 0):
            print(e.code if isinstance(e.code, str) else 'ошибка %s' % e.code)
            rc = 1
    if frozen:
        input('\nНажмите Enter, чтобы закрыть окно.')
    sys.exit(rc)


if __name__ == '__main__':
    main()
