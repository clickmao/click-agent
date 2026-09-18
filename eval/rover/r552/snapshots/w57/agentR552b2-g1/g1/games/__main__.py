"""CLI entry: python3 -m games <game_id> reads stdin, writes stdout."""

import sys

from . import life, nim, sub, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in _MODULES:
        return 2
    text = sys.stdin.read()
    out = _MODULES[argv[1]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
