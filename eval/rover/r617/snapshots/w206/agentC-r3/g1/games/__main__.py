import sys

from games.life import solve as life_solve
from games.sub import solve as sub_solve
from games.nim import solve as nim_solve
from games.wythoff import solve as wythoff_solve

MODULES = {
    "life": life_solve,
    "sub": sub_solve,
    "nim": nim_solve,
    "wythoff": wythoff_solve,
}


def main():
    game_id = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in MODULES else None
    text = sys.stdin.read()
    if game_id is None:
        return
    out = MODULES[game_id](text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
