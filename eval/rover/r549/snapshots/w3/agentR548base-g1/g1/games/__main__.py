"""CLI entry: python3 -m games <life|sub|nim|wythoff>, reads stdin, writes result to stdout."""

import sys

from . import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] not in MODULES:
        return 1
    data = sys.stdin.read()
    out = MODULES[args[0]].solve(data)
    if out:
        sys.stdout.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
