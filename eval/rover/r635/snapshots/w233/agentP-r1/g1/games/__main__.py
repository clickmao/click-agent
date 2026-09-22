"""CLI entry: python3 -m games <game_id> reads stdin, writes solve() result."""
import sys

from games import life, sub, nim, wythoff

_REGISTRY = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    args = sys.argv[1:]
    if not args or args[0] not in _REGISTRY:
        return 1
    mod = _REGISTRY[args[0]]
    data = sys.stdin.read()
    sys.stdout.write(mod.solve(data))
    return 0


if __name__ == '__main__':
    sys.exit(main())
