import sys

from . import life, sub, nim, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main() -> None:
    game = sys.argv[1]
    data = sys.stdin.read()
    sys.stdout.write(_GAMES[game](data))


if __name__ == "__main__":
    main()
