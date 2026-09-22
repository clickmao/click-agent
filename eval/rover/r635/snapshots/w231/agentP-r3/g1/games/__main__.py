"""CLI entry: python3 -m games <game_id>."""

import sys


def main():
    args = sys.argv[1:]
    if not args:
        return 0
    game_id = args[0]
    text = sys.stdin.read()
    if game_id == "life":
        from . import life as mod
    elif game_id == "sub":
        from . import sub as mod
    elif game_id == "nim":
        from . import nim as mod
    elif game_id == "wythoff":
        from . import wythoff as mod
    else:
        return 1
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
