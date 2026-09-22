"""CLI: python3 -m games <game_id> reads stdin and writes the game result."""

import sys

from . import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    game_id = argv[1]
    text = sys.stdin.read()
    out = MODULES[game_id].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main(sys.argv)
