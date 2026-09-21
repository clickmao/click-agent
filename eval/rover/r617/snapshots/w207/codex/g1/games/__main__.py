"""CLI entry point: python3 -m games <game_id>."""

import sys

from . import life, nim, sub, wythoff

GAMES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> None:
    game_id = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(GAMES[game_id].solve(text))


if __name__ == "__main__":
    main()
