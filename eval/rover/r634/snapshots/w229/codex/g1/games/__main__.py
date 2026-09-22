import sys

from . import life, sub, nim, wythoff

GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(GAMES[game_id](text))


if __name__ == "__main__":
    main()
