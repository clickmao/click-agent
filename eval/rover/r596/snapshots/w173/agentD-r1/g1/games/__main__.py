"""CLI entry point: python3 -m games <game_id>."""

import sys


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    game = sys.argv[1]
    mods = {
        "life": "games.life",
        "sub": "games.sub",
        "nim": "games.nim",
        "wythoff": "games.wythoff",
    }
    name = mods.get(game)
    if name is None:
        return 1
    module = __import__(name, fromlist=["solve"])
    text = sys.stdin.read()
    out = module.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
