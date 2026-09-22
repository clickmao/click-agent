"""CLI entry: python3 -m games <game_id>."""
import sys

GAMES = ('life', 'sub', 'nim', 'wythoff')


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in GAMES:
        return
    name = 'games.' + sys.argv[1]
    mod = __import__(name, fromlist=['solve'])
    data = sys.stdin.read()
    sys.stdout.write(mod.solve(data))


if __name__ == '__main__':
    main()
