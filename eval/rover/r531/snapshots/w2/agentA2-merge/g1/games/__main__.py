"""CLI entry: python3 -m games <game_id>  (game_id in life/sub/nim/wythoff).

Reads all of stdin, dispatches to the game module's solve(), writes the
returned text to stdout (no extra output, stderr silent on success).

Usage:
    python3 -m games <game_id>     # package form
    python3 games/__main__.py <game_id>   # direct file form
"""

import os
import sys

_IDS = ('life', 'sub', 'nim', 'wythoff')


def _load(game_id):
    if game_id not in _IDS:
        return None
    if __package__ in (None, ''):
        # Executed directly as a file: no package context, import as top level.
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        mod = __import__(game_id)
    else:
        mod = __import__(__package__ + '.' + game_id, {}, {}, [game_id])
    return mod


def main(argv):
    if len(argv) < 2:
        return 2
    mod = _load(argv[1])
    if mod is None:
        return 2
    sys.stdout.write(mod.solve(sys.stdin.read()))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
