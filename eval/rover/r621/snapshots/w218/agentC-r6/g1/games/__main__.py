"""CLI entry point: python3 -m games <game_id>."""

import sys

from games import life, sub, nim, wythoff

_MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main() -> None:
    game_id = sys.argv[1] if len(sys.argv) > 1 else ''
    mod = _MODULES[game_id]
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    sys.stdout.flush()


if __name__ == '__main__':
    main()
