import sys

from games import life, sub, nim, wythoff

GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in GAMES:
        return 1
    data = sys.stdin.read()
    out = GAMES[args[0]].solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
