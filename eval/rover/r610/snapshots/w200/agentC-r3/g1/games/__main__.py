"""CLI entry point: python3 -m games <game_id> (life|sub|nim|wythoff)."""

import sys

from games import life, nim, sub, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> int:
    game_id = sys.argv[1]
    text = sys.stdin.read()
    out = MODULES[game_id].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
