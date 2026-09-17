"""CLI 入口: python3 -m games <game_id>  (life/sub/nim/wythoff)。"""
import sys

_MODS = {
    "life": "games.life",
    "sub": "games.sub",
    "nim": "games.nim",
    "wythoff": "games.wythoff",
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in _MODS:
        return 2
    import importlib

    mod = importlib.import_module(_MODS[sys.argv[1]])
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
