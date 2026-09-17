import sys

from . import life

GAMES = {
    'life': life.solve,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in GAMES:
        return 0
    sys.stdout.write(GAMES[sys.argv[1]](sys.stdin.read()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
