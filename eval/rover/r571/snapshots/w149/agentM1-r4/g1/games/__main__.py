"""CLI entry point: python3 -m games <game_id> reads stdin and writes solve()'s result."""

import sys

from games import life, nim, sub, wythoff

_GAMES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main(argv):
    if len(argv) < 2 or argv[1] not in _GAMES:
        return 2
    text = sys.stdin.read()
    out = _GAMES[argv[1]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
