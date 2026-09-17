"""CLI entry: python3 -m games <game_id>  (life|sub|nim|wythoff)."""

import sys

from . import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) < 2:
        return 1
    game_id = argv[1]
    mod = _MODULES.get(game_id)
    if mod is None:
        return 1
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
