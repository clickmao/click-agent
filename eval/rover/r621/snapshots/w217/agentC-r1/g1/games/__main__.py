import sys

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    args = sys.argv[1:]
    game_id = args[0] if args else ''
    text = sys.stdin.read()
    mod = _MODULES[game_id]
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
