"""CLI 入口: python3 -m games <game_id>。"""
import importlib
import sys

_GAMES = {'life', 'sub', 'nim', 'wythoff'}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in _GAMES:
        return 1
    mod = importlib.import_module('games.' + sys.argv[1])
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
