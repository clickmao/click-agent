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
    if len(sys.argv) < 2:
        return
    game = GAMES.get(sys.argv[1])
    if game is None:
        return
    text = sys.stdin.read()
    sys.stdout.write(game(text))


if __name__ == '__main__':
    main()
