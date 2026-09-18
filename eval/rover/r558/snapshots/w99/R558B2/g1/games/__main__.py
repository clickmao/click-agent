"""CLI entry point: python3 -m games <game_id> reads all of stdin and writes
solve()'s return value (no trailing newline added by us) to stdout."""

import sys


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    game_id = sys.argv[1]
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
        return 1
    out = solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
