"""CLI entry: python3 -m games <game_id>."""

import sys


def main():
    game_id = sys.argv[1] if len(sys.argv) > 1 else ""
    data = sys.stdin.read()
    if game_id == "life":
        from games.life import solve
    elif game_id == "sub":
        from games.sub import solve
    elif game_id == "nim":
        from games.nim import solve
    elif game_id == "wythoff":
        from games.wythoff import solve
    else:
        return
    sys.stdout.write(solve(data))


if __name__ == "__main__":
    main()
