import sys

from . import life, nim, sub, wythoff

GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main() -> None:
    game_id = sys.argv[1]
    data = sys.stdin.read()
    sys.stdout.write(GAMES[game_id](data))


if __name__ == "__main__":
    main()
