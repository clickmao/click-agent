import sys

from games import life, sub, nim, wythoff

GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        return 1
    game_id = argv[0]
    fn = GAMES.get(game_id)
    if fn is None:
        return 1
    data = sys.stdin.read()
    out = fn(data)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
