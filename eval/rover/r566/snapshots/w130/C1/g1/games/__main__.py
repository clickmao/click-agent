"""CLI entry point: python3 -m games <game_id> < stdin > stdout."""
import sys


def main() -> None:
    if len(sys.argv) < 2:
        return
    game_id = sys.argv[1]
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
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == "__main__":
    main()
