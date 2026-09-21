import sys

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    if len(sys.argv) < 2:
        return
    game_id = sys.argv[1]
    mod = _MODULES.get(game_id)
    if mod is None:
        return
    data = sys.stdin.read()
    sys.stdout.write(mod.solve(data))


if __name__ == '__main__':
    main()
