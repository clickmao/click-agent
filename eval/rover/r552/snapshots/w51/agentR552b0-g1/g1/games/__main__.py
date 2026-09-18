"""CLI entry: python3 -m games <game_id>."""

import sys

from games import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in _MODULES:
        return 2
    text = sys.stdin.read()
    out = _MODULES[sys.argv[1]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
