"""CLI entry point: python3 -m games <game_id>."""

import sys

from games import life, nim, sub, wythoff

_MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(_MODULES[game_id].solve(text))


if __name__ == '__main__':
    main()
