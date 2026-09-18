import sys

from games.life import solve as life_solve
from games.sub import solve as sub_solve
from games.nim import solve as nim_solve
from games.wythoff import solve as wythoff_solve

_SOLVERS = {
    'life': life_solve,
    'sub': sub_solve,
    'nim': nim_solve,
    'wythoff': wythoff_solve,
}


def main():
    argv = sys.argv[1:]
    if not argv:
        return
    game = argv[0]
    if game not in _SOLVERS:
        return
    text = sys.stdin.read()
    out = _SOLVERS[game](text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
