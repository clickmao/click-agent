"""CLI entry point: python3 -m games <game_id>."""

import sys

from games import life, nim, sub, wythoff

GAMES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in GAMES:
        return
    text = sys.stdin.read()
    sys.stdout.write(GAMES[argv[1]].solve(text))


if __name__ == "__main__":
    main(sys.argv)
