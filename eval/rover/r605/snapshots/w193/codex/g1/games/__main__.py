import sys

from . import life, nim, sub, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main() -> None:
    solve = _GAMES[sys.argv[1]]
    sys.stdout.write(solve(sys.stdin.read()))


if __name__ == "__main__":
    main()
