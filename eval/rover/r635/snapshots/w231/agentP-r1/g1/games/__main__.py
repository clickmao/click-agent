"""CLI entry point: python3 -m games <game_id> < input."""

import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> int:
    argv = sys.argv[1:]
    if len(argv) < 1:
        return 2
    game_id = argv[0]
    mod = _MODULES.get(game_id)
    if mod is None:
        return 2
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
