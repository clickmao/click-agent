import sys

from . import life, sub, nim, wythoff

_GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    args = sys.argv[1:]
    if not args or args[0] not in _GAMES:
        return
    text = sys.stdin.read()
    out = _GAMES[args[0]].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
