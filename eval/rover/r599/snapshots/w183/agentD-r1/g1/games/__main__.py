"""CLI entry: python3 -m games <game_id> reads stdin and writes solve()'s output."""

import sys


def main():
    argv = sys.argv[1:]
    if len(argv) != 1 or argv[0] not in ("life", "sub", "nim", "wythoff"):
        return
    game_id = argv[0]
    if game_id == "life":
        from games.life import solve
    elif game_id == "sub":
        from games.sub import solve
    elif game_id == "nim":
        from games.nim import solve
    else:
        from games.wythoff import solve
    text = sys.stdin.read()
    sys.stdout.write(solve(text))


if __name__ == "__main__":
    main()
