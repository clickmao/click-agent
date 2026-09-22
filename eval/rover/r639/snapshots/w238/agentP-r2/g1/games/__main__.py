"""CLI entry: python3 -m games <game_id>, game_id in {life,sub,nim,wythoff}."""
import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> int:
    game = sys.argv[1]
    text = sys.stdin.read()
    out = _MODULES[game].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
