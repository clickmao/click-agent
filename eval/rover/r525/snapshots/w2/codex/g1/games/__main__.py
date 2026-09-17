"""Command line entry point: python3 -m games <game_id>."""

import sys

from . import life, nim, sub, wythoff

GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    handler = GAMES.get(sys.argv[1])
    if handler is None:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(handler(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
