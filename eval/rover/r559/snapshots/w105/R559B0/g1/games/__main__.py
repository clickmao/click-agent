"""CLI entry: python3 -m games <game_id>."""

import sys

from games import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    game_id = sys.argv[1]
    mod = _MODULES[game_id]
    data = sys.stdin.read()
    sys.stdout.write(mod.solve(data))


if __name__ == "__main__":
    main()
