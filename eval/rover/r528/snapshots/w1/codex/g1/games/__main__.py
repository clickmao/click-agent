"""CLI entry point: python3 -m games <game_id>."""

import sys

from . import life, nim, sub, wythoff

GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main() -> None:
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in GAMES:
        return
    text = sys.stdin.read()
    sys.stdout.write(GAMES[args[0]](text))


if __name__ == "__main__":
    main()
