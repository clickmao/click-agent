"""CLI entry: python3 -m games <game_id>; reads all stdin, calls module solve, writes stdout."""

import sys

from games import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> int:
    game_id = sys.argv[1] if len(sys.argv) > 1 else ""
    mod = _MODULES.get(game_id)
    if mod is None:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
