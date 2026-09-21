"""CLI entry point: python3 -m games <game_id>."""

import sys


def main() -> None:
    game_id = sys.argv[1] if len(sys.argv) > 1 else ""
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
        return
    sys.stdout.write(mod.solve(text))


if __name__ == "__main__":
    main()
