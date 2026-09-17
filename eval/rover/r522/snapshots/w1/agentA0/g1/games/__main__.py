"""CLI entry: python3 -m games <game_id>, reads stdin, writes stdout."""

import sys
from importlib import import_module

_GAMES = {
    'life': 'games.life',
    'sub': 'games.sub',
    'nim': 'games.nim',
    'wythoff': 'games.wythoff',
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in _GAMES:
        sys.exit(2)
    mod = import_module(_GAMES[sys.argv[1]])
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
