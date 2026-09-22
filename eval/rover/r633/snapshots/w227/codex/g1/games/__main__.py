import sys

from . import life, nim, sub, wythoff

_GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    game = argv[0]
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[game](text))


if __name__ == '__main__':
    main()
