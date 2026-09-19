import sys

from . import life, nim, sub, wythoff

GAMES_BY_ID = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(GAMES_BY_ID[game_id](text))


if __name__ == "__main__":
    main()
