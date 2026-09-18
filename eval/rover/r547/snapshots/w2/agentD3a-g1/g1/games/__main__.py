import sys

from . import life, sub, nim, wythoff

GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in GAMES:
        return
    text = sys.stdin.read()
    sys.stdout.write(GAMES[args[0]].solve(text))


if __name__ == '__main__':
    main()
