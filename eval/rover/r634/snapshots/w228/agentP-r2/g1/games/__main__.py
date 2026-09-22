import sys

MODULES = {}


def _load():
    if MODULES:
        return MODULES
    from games import life, sub, nim, wythoff
    MODULES.update({'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff})
    return MODULES


def main():
    argv = sys.argv[1:]
    if not argv:
        return
    game_id = argv[0]
    mods = _load()
    mod = mods.get(game_id)
    if mod is None:
        return
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
