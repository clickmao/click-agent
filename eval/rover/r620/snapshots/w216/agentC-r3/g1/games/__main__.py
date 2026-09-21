import sys

from games.life import solve as life_solve
from games.sub import solve as sub_solve
from games.nim import solve as nim_solve
from games.wythoff import solve as wythoff_solve

_MODULES = {
    'life': life_solve,
    'sub': sub_solve,
    'nim': nim_solve,
    'wythoff': wythoff_solve,
}


def main():
    game = sys.argv[1]
    data = sys.stdin.read()
    out = _MODULES[game](data)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
