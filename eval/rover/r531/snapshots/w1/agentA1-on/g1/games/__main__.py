"""CLI entry point: python3 -m games <game_id>

Reads the whole of stdin, dispatches to the game module's ``solve`` and writes
the returned text to stdout verbatim (no extra output anywhere).
"""

import importlib
import sys

_GAMES = ("life", "sub", "nim", "wythoff")


def main(argv: list) -> int:
    if len(argv) != 2 or argv[1] not in _GAMES:
        return 2
    module = importlib.import_module("games." + argv[1])
    text = sys.stdin.read()
    sys.stdout.write(module.solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
