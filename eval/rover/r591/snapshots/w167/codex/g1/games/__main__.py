"""CLI entry point: python3 -m games <game_id>."""

import sys

from . import life, nim, sub, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main(argv=None):
    argv = sys.argv if argv is None else argv
    game_id = argv[1]
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[game_id](text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
