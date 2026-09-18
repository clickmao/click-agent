"""CLI: python3 -m games <game_id>, reads stdin, writes solve() output."""

import sys


def main():
    args = sys.argv[1:]
    game = args[0] if args else ""
    text = sys.stdin.read()
    if game == "life":
        from games import life as mod
    elif game == "sub":
        from games import sub as mod
    elif game == "nim":
        from games import nim as mod
    elif game == "wythoff":
        from games import wythoff as mod
    else:
        return 1
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
