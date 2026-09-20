import sys

from games import life, nim, sub, wythoff

_GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main() -> None:
    if len(sys.argv) < 2:
        return
    fn = _GAMES.get(sys.argv[1])
    if fn is None:
        return
    text = sys.stdin.read()
    sys.stdout.write(fn(text))


if __name__ == '__main__':
    main()
