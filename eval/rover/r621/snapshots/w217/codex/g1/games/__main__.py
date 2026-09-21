"""CLI entry point: python3 -m games <game_id>."""

import sys

from . import life, nim, sub, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> int:
    game = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(MODULES[game].solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
