import sys

from .life import solve as life_solve
from .sub import solve as sub_solve
from .nim import solve as nim_solve
from .wythoff import solve as wythoff_solve

MODULES = {
    'life': life_solve,
    'sub': sub_solve,
    'nim': nim_solve,
    'wythoff': wythoff_solve,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in MODULES:
        return 2
    game = argv[1]
    text = sys.stdin.read()
    sys.stdout.write(MODULES[game].solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
