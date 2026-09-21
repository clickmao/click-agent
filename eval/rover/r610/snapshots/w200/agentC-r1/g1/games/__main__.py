"""CLI entry: python3 -m games <game_id>."""
import sys

from games import life, nim, sub, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _MODULES:
        return 2
    data = sys.stdin.read()
    out = _MODULES[argv[0]].solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
