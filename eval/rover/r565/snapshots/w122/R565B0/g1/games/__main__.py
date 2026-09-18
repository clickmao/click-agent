import sys

from games.life import solve as solve_life
from games.sub import solve as solve_sub
from games.nim import solve as solve_nim
from games.wythoff import solve as solve_wythoff

MODULES = {
    "life": solve_life,
    "sub": solve_sub,
    "nim": solve_nim,
    "wythoff": solve_wythoff,
}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    result = MODULES[game_id](text)
    sys.stdout.write(result)


if __name__ == "__main__":
    main()
