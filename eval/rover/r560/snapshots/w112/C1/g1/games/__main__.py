"""CLI entry point: python3 -m games <game_id>."""

import sys

from .life import solve as life_solve
from .sub import solve as sub_solve
from .nim import solve as nim_solve
from .wythoff import solve as wythoff_solve

GAMES = {
    'life': life_solve,
    'sub': sub_solve,
    'nim': nim_solve,
    'wythoff': wythoff_solve,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in GAMES:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(GAMES[argv[0]](text))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
