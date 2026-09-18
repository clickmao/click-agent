import sys

from . import life, nim, sub, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _GAMES:
        return 1
    text = sys.stdin.read()
    out = _GAMES[argv[0]](text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
