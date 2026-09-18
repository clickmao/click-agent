import sys

from . import life, sub, nim, wythoff

_GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in _GAMES:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[argv[1]].solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
