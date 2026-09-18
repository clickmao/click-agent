"""CLI entry point: python3 -m games <game_id>"""

import sys

from . import life, sub, nim, wythoff

_GAMES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    game_id = sys.argv[1]
    mod = _GAMES[game_id]
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main()
