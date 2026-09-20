"""CLI entry point: python3 -m games <game_id>."""

import sys

from . import life, nim, sub, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in MODULES:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(MODULES[argv[1]].solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
