"""CLI entry: python3 -m games <game_id>  (life|sub|nim|wythoff)."""

import sys

from . import life, nim, sub, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in _GAMES:
        return 2
    text = sys.stdin.read()
    out = _GAMES[argv[0]](text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
