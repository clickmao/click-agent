"""CLI entry: python3 -m games <game_id> with game_id in life/sub/nim/wythoff."""

import importlib
import sys

MODULES = {
    "life": "games.life",
    "sub": "games.sub",
    "nim": "games.nim",
    "wythoff": "games.wythoff",
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in MODULES:
        return
    mod = importlib.import_module(MODULES[sys.argv[1]])
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == "__main__":
    main()
