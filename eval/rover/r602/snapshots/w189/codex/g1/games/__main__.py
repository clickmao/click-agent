"""CLI entry point: python3 -m games <game_id>."""

import sys

from . import life, nim, sub, wythoff

GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in GAMES:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(GAMES[sys.argv[1]](text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
