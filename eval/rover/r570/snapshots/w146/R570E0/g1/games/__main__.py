import sys

from . import life, sub, nim, wythoff

HANDLERS = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main():
    if len(sys.argv) < 2:
        return 1
    game_id = sys.argv[1]
    handler = HANDLERS.get(game_id)
    if handler is None:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(handler(text))
    return 0


if __name__ == '__main__':
    sys.exit(main())
