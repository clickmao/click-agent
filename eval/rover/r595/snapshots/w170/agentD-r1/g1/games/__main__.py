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


def main():
    game = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(MODULES[game](text))


if __name__ == '__main__':
    main()
