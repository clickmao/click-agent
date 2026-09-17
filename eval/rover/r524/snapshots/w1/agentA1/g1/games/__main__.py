"""CLI entry point: ``python3 -m games <game_id>``.

Reads all of stdin, dispatches to the game module's ``solve``, writes the
returned text to stdout (no extra newline, silent stderr).
"""

import sys

from games import life, sub, nim, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _GAMES:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[argv[0]](text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
