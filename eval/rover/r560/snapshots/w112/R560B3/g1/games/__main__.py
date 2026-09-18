import sys

from games import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    if len(sys.argv) < 2:
        return 1
    game_id = sys.argv[1]
    mod = MODULES.get(game_id)
    if mod is None:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main())
