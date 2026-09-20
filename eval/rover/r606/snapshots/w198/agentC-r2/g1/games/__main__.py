import sys

from . import life, sub, nim, wythoff

_GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    game = argv[1]
    text = sys.stdin.read()
    solve = _GAMES[game].solve
    out = solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main(sys.argv)
