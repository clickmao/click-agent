"""CLI entry point: python3 -m games <game_id>."""

import sys

from . import life, nim, sub, wythoff

GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main(argv):
    game_id = argv[1]
    text = sys.stdin.read()
    sys.stdout.write(GAMES[game_id](text))


if __name__ == "__main__":
    main(sys.argv)
