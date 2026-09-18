import sys

from . import life, nim, sub, wythoff

GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in GAMES:
        return
    sys.stdout.write(GAMES[sys.argv[1]](sys.stdin.read()))


if __name__ == "__main__":
    main()
