"""CLI entry: python3 -m games <game_id>."""
import sys

from games import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    if len(sys.argv) < 2:
        return
    game_id = sys.argv[1]
    mod = MODULES.get(game_id)
    if mod is None:
        return
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == "__main__":
    main()
