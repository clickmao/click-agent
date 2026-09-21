"""CLI entry: python3 -m games <game_id>

Reads all of stdin, dispatches to the named game module's solve(),
and writes the returned text to stdout with no trailing newline added.
"""

import sys


def main(argv):
    if len(argv) < 2:
        return 1
    game_id = argv[1]
    import importlib
    try:
        mod = importlib.import_module('games.' + game_id)
    except Exception:
        return 1
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
