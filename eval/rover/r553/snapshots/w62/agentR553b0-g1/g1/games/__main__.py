"""CLI entry: python3 -m games <game_id>; reads all stdin, writes solve() result."""

import sys

from games import life, nim, sub, wythoff

_MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main() -> int:
    game_id = sys.argv[1] if len(sys.argv) > 1 else ''
    mod = _MODULES.get(game_id)
    if mod is None:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main())
