import sys

from . import life, nim, sub, wythoff

_GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main(argv):
    game = argv[1]
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[game](text))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
