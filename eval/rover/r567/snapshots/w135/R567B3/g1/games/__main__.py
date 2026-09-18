"""CLI entry: python3 -m games <game_id>."""

import sys

from games import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    if len(sys.argv) != 2:
        return
    mod = MODULES.get(sys.argv[1])
    if mod is None:
        return
    out = mod.solve(sys.stdin.read())
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
