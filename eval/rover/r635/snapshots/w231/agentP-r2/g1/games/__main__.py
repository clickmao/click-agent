"""CLI entry point: python3 -m games <game_id> with game_id in life/sub/nim/wythoff."""

import sys

from games.life import solve as life_solve
from games.sub import solve as sub_solve
from games.nim import solve as nim_solve
from games.wythoff import solve as wythoff_solve

MODULES = {
    'life': life_solve,
    'sub': sub_solve,
    'nim': nim_solve,
    'wythoff': wythoff_solve,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in MODULES:
        return 1
    data = sys.stdin.read()
    out = MODULES[argv[1]](data)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
