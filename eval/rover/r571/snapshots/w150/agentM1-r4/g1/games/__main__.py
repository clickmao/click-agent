"""CLI entry: python3 -m games <game_id> reads stdin and writes the answer."""

import sys


def main() -> int:
    if len(sys.argv) != 2:
        return 1
    game = sys.argv[1]
    mods = {
        "life": "games.life",
        "sub": "games.sub",
        "nim": "games.nim",
        "wythoff": "games.wythoff",
    }
    if game not in mods:
        return 1
    import importlib
    mod = importlib.import_module(mods[game])
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
