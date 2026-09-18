"""CLI entry point: ``python3 -m games <game_id>``.

Reads all of stdin, dispatches to the game's ``solve`` and writes the result
to stdout.  Nothing is printed to stderr.
"""

import sys

from . import life, nim, sub, wythoff

_GAMES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    """Run the requested game. Returns a process exit code."""
    if len(argv) != 2 or argv[1] not in _GAMES:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[argv[1]].solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
