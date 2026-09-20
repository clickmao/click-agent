"""CLI entry point: python3 -m games <game_id>."""

import sys


def main():
    if len(sys.argv) < 2:
        return
    game_id = sys.argv[1]
    mod = __import__('games.' + game_id, fromlist=['solve'])
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
