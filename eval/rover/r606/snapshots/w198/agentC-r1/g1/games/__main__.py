"""CLI 入口：python3 -m games <game_id>"""

import sys


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        return 2
    game_id = argv[0]
    if game_id == "life":
        from games.life import solve
    elif game_id == "sub":
        from games.sub import solve
    elif game_id == "nim":
        from games.nim import solve
    elif game_id == "wythoff":
        from games.wythoff import solve
    else:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
