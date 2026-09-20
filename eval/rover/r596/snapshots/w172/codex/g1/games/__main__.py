import sys

from . import life, nim, sub, wythoff

GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main() -> None:
    game = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(GAMES[game](text))


if __name__ == '__main__':
    main()
