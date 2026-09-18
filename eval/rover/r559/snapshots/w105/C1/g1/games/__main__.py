import sys

from games import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in MODULES:
        return
    game = MODULES[sys.argv[1]]
    text = sys.stdin.read()
    sys.stdout.write(game.solve(text))


if __name__ == '__main__':
    main()
