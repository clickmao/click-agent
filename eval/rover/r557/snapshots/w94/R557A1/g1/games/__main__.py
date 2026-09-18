"""CLI entry point: python3 -m games <game_id>."""

import sys


def main() -> int:
    game_id = sys.argv[1]
    text = sys.stdin.read()
    module = __import__('games.' + game_id, fromlist=['solve'])
    sys.stdout.write(module.solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main())
