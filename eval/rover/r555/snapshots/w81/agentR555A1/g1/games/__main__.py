"""CLI 入口: python3 -m games <game_id>"""

import sys


def main() -> int:
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
        return 0
    out = solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
