"""CLI entry point: ``python3 -m games <game_id>``."""

import sys

from . import life, nim, sub, wythoff

_SOLVERS = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main(argv):
    if len(argv) < 2 or argv[1] not in _SOLVERS:
        return 1
    text = sys.stdin.read()
    result = _SOLVERS[argv[1]](text)
    if result:
        sys.stdout.write(result)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
