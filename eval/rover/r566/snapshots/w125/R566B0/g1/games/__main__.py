"""CLI entry: python3 -m games <game_id>, reading stdin and writing solve() output."""

import sys

from . import life
from . import sub
from . import nim
from . import wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    game_id = sys.argv[1]
    mod = _MODULES.get(game_id)
    if mod is None:
        return 2
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
