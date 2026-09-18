"""CLI entry point: python3 -m games <game_id>."""

import sys

from . import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in MODULES:
        sys.exit(2)
    text = sys.stdin.read()
    out = MODULES[sys.argv[1]].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
