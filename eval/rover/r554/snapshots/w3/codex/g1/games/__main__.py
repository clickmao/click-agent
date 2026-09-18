import sys

from . import life, sub, nim, wythoff

GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in GAMES:
        return
    text = sys.stdin.read()
    sys.stdout.write(GAMES[sys.argv[1]](text))


if __name__ == '__main__':
    main()
