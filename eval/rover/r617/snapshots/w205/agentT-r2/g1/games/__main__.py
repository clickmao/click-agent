"""CLI entry point: python3 -m games <game_id>."""

import sys


def main() -> int:
    game_id = sys.argv[1]
    if game_id == "life":
        from games import life as mod
    elif game_id == "sub":
        from games import sub as mod
    elif game_id == "nim":
        from games import nim as mod
    elif game_id == "wythoff":
        from games import wythoff as mod
    else:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
