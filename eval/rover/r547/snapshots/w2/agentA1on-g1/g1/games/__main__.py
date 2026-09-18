"""CLI entry: python3 -m games <game_id>  (game_id in life/sub/nim/wythoff)."""

import sys

from . import life, nim, sub, wythoff

_GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main(argv) -> int:
    if len(argv) != 2 or argv[1] not in _GAMES:
        return 2
    text = sys.stdin.read()
    result = _GAMES[argv[1]](text)
    sys.stdout.write(result)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
