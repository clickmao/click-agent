import sys

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    argv = sys.argv[1:]
    if not argv:
        return 1
    game = argv[0]
    mod = _MODULES.get(game)
    if mod is None:
        return 1
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
