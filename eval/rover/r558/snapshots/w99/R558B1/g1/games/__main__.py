import sys

from games import life, sub, nim, wythoff

GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    out = GAMES[game_id](text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
