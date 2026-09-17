"""CLI entry: ``python3 -m games <game_id>`` reads all of stdin, writes solve() result."""

import sys

from games import life, nim, sub, wythoff

_GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in _GAMES:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[argv[1]](text))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
