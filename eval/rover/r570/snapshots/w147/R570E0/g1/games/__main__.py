"""CLI entry: python3 -m games <game_id>

Reads all of stdin, dispatches to the game module's solve(), writes the
result to stdout with no trailing newline and no extra output.
"""

import sys
from . import life, sub, nim, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in _GAMES:
        return 2
    out = _GAMES[argv[1]](sys.stdin.read())
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
