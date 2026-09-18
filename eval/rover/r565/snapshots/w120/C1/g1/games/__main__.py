"""CLI entry point: python3 -m games <game_id>."""

import sys

from . import life, nim, sub, wythoff

_GAMES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _GAMES:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[argv[0]].solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
