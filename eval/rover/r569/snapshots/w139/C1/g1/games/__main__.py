import sys

from . import life, sub, nim, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] not in _GAMES:
        return
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[args[0]](text))


if __name__ == "__main__":
    main()
