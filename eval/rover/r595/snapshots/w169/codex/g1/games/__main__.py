import sys

from . import life, nim, sub, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in _GAMES:
        return 1
    text = sys.stdin.read()
    out = _GAMES[sys.argv[1]](text)
    if out:
        sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
