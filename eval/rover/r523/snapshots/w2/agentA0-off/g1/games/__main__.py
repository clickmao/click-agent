"""CLI entry: python3 -m games <game_id>

Reads all of stdin, delegates to the game module's solve(), writes stdout.
"""

import sys

_MODULES = {
    "life": "games.life",
    "sub": "games.sub",
    "nim": "games.nim",
    "wythoff": "games.wythoff",
}


def main(argv):
    if len(argv) < 2:
        return 2
    game_id = argv[1]
    if game_id not in _MODULES:
        return 2

    import importlib

    module = importlib.import_module(_MODULES[game_id])
    data = sys.stdin.read()
    out = module.solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
