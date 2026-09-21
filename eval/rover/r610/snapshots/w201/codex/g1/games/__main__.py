import sys

from . import life, nim, sub, wythoff

_GAMES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> None:
    game = _GAMES[sys.argv[1]]
    text = sys.stdin.read()
    sys.stdout.write(game.solve(text))


if __name__ == "__main__":
    main()
