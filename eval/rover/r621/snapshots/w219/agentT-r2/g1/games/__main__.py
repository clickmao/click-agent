"""CLI entry: python3 -m games <game_id>."""

import sys

from games import life, nim, sub, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _MODULES:
        return 1
    mod = _MODULES[argv[0]]
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
