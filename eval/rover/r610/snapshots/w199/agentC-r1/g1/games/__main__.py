"""CLI entry point: python3 -m games <game_id>

Reads all of stdin, dispatches to games.<game_id>.solve, writes the
return value to stdout with no extra characters (no trailing newline).
"""

import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    game_id = argv[1]
    text = sys.stdin.read()
    out = _MODULES[game_id].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
