"""CLI entry point: python3 -m games <game_id>."""

import sys

from games import life
from games import nim
from games import sub
from games import wythoff

_GAMES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] not in _GAMES:
        return
    text = sys.stdin.read()
    out = _GAMES[argv[0]].solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
