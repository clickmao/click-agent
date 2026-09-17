"""CLI entry: python3 -m games <game_id>  (game_id in life/sub/nim/wythoff).

Reads all of stdin, dispatches to the module's solve(), writes result to stdout
without any extra text and without a trailing newline.
"""

import sys

from . import life, nim, sub, wythoff

_GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in _GAMES:
        return 1
    data = sys.stdin.read()
    out = _GAMES[argv[1]](data)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
