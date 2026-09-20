import sys

from . import life, nim, sub, wythoff

GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game = sys.argv[1]
    text = sys.stdin.read()
    out = GAMES[game].solve(text)
    if out:
        sys.stdout.write(out)


if __name__ == '__main__':
    main()
