"""CLI entry: python3 -m games <game_id>."""

import sys

from .life import solve as life_solve
from .sub import solve as sub_solve
from .nim import solve as nim_solve
from .wythoff import solve as wythoff_solve

_GAMES = {
    "life": life_solve,
    "sub": sub_solve,
    "nim": nim_solve,
    "wythoff": wythoff_solve,
}


def main(argv):
    if len(argv) < 2 or argv[1] not in _GAMES:
        return 1
    text = sys.stdin.read()
    out = _GAMES[argv[1]](text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
