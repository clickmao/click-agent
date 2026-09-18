"""CLI entry point: python3 -m games <game_id>."""

import sys

from . import life, nim, sub, wythoff

GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in GAMES:
        sys.exit(1)
    text = sys.stdin.read()
    out = GAMES[sys.argv[1]](text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
