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
    text = sys.stdin.read()
    out = GAMES[args[0]].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
