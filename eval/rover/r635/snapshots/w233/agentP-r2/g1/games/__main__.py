import sys

from games import life, sub, nim, wythoff

_GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    args = sys.argv[1:]
    game = _GAMES[args[0]]
    text = sys.stdin.read()
    out = game.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
