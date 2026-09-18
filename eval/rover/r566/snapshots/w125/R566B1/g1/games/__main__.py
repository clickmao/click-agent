"""CLI entry: python3 -m games <game_id> reads stdin, writes stdout."""

import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    game_id = sys.argv[1]
    mod = _MODULES.get(game_id)
    if mod is None:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main())
