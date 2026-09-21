"""CLI entry: python3 -m games <game_id> with game_id in {life, sub, nim, wythoff}."""

import sys


def main():
    argv = sys.argv[1:]
    game_id = argv[0] if argv else ""
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
        sys.exit(2)
    sys.stdout.write(solve(data))


if __name__ == "__main__":
    main()
