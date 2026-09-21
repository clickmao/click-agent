"""CLI 入口：python3 -m games <game_id>"""
import sys


def main() -> None:
    game = sys.argv[1] if len(sys.argv) > 1 else ""
    if game == "life":
        from games import life as mod
    elif game == "sub":
        from games import sub as mod
    elif game == "nim":
        from games import nim as mod
    elif game == "wythoff":
        from games import wythoff as mod
    else:
        sys.exit(1)
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == "__main__":
    main()
