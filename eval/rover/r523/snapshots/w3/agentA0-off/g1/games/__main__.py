"""CLI entry: python3 -m games <game_id>, reads stdin, writes stdout."""

import sys

from . import life, sub, nim, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in _GAMES:
        return 2
    text = sys.stdin.read()
    out = _GAMES[sys.argv[1]](text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
