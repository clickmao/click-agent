# games/__main__.py
"""CLI entry: python3 -m games <game_id>  (game_id in life/sub/nim/wythoff)."""

import os
import sys

if __package__ in (None, ''):
    # Direct-script mode (`python3 -I games/__main__.py`): no package context,
    # so relative imports are impossible -- fall back to absolute ones.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from games import life, sub, nim, wythoff
else:
    from . import life, sub, nim, wythoff


def _dispatch(game_id, text):
    mod = {
        'life': life,
        'sub': sub,
        'nim': nim,
        'wythoff': wythoff,
    }.get(game_id)
    if mod is None:
        raise SystemExit(1)
    return mod.solve(text)


def main():
    argv = sys.argv
    if len(argv) < 2:
        return 1
    game_id = argv[1]
    text = sys.stdin.read()
    out = _dispatch(game_id, text)
    if out:
        sys.stdout.buffer.write(out.encode('utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
