"""CLI entry: python3 -m games <game_id>  (life|sub|nim|wythoff)."""
import sys


def main() -> int:
    if len(sys.argv) < 2:
        return 2
    game_id = sys.argv[1]
    mods = {"life": "games.life", "sub": "games.sub",
            "nim": "games.nim", "wythoff": "games.wythoff"}
    if game_id not in mods:
        return 2
    mod = __import__(mods[game_id], fromlist=["solve"])
    sys.stdout.write(mod.solve(sys.stdin.read()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
