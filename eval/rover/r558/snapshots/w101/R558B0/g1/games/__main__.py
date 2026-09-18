"""CLI entry: python3 -m games <game_id> reads stdin, writes solver stdout.
"""

import sys

from games import life, nim, sub, wythoff

_SOLVERS = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _SOLVERS:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(_SOLVERS[argv[0]](text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
