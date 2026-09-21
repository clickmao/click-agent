"""CLI entry: python3 -m games <game_id>"""
import sys
from importlib import import_module


def main():
    argv = sys.argv[1:]
    if not argv:
        return
    game_id = argv[0]
    mod = import_module('games.' + game_id)
    text = sys.stdin.read()
    out = mod.solve(text)
    if out:
        sys.stdout.write(out)


if __name__ == '__main__':
    main()
