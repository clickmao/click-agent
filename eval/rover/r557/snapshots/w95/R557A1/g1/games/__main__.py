"""CLI entry point: python3 -m games <game_id> reads stdin and prints stdout."""

import sys


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    game = sys.argv[1]
    if game == "life":
        from games.life import solve
    elif game == "sub":
        from games.sub import solve
    elif game == "nim":
        from games.nim import solve
    elif game == "wythoff":
        from games.wythoff import solve
    else:
        return 1

    text = sys.stdin.read()
    sys.stdout.write(solve(text))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
