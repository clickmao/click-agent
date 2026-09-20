"""CLI entry point: python3 -m games <game_id>"""
import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> int:
    game_id = sys.argv[1]
    text = sys.stdin.read()
    mod = _MODULES[game_id]
    sys.stdout.write(mod.solve(text))
    sys.stdout.flush()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
