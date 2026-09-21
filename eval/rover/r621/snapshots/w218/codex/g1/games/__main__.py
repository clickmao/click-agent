import sys

from games import life, sub, nim, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in _GAMES:
        return
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[argv[1]](text))


if __name__ == "__main__":
    main(sys.argv)
