import sys

from . import life, nim, sub, wythoff

GAMES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> None:
    game = GAMES[sys.argv[1]]
    data = sys.stdin.read()
    sys.stdout.write(game.solve(data))


if __name__ == "__main__":
    main()
