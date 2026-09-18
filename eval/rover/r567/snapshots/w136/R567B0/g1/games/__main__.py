import sys

from games.life import solve as life_solve
from games.sub import solve as sub_solve
from games.nim import solve as nim_solve
from games.wythoff import solve as wythoff_solve

SOLVERS = {
    'life': life_solve,
    'sub': sub_solve,
    'nim': nim_solve,
    'wythoff': wythoff_solve,
}


def main():
    if len(sys.argv) < 2:
        return
    game_id = sys.argv[1]
    solver = SOLVERS.get(game_id)
    if solver is None:
        return
    text = sys.stdin.read()
    out = solver(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
