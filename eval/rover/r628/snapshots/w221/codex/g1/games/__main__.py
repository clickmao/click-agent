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
    if len(argv) != 2 or argv[1] not in GAMES:
        return 1
    text = sys.stdin.read()
    out = GAMES[argv[1]](text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
