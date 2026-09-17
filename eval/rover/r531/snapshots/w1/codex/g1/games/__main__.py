"""CLI entry: python3 -m games <game_id>."""

import sys

from . import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> None:
    if len(sys.argv) < 2:
        return
    module = MODULES.get(sys.argv[1])
    if module is None:
        return
    text = sys.stdin.read()
    sys.stdout.write(module.solve(text))


if __name__ == "__main__":
    main()
