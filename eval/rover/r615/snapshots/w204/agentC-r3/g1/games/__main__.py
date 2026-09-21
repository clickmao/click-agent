"""CLI 入口：python3 -m games <game_id>，game_id 属于 life/sub/nim/wythoff。"""

import sys


def main() -> None:
    argv = sys.argv[1:]
    if not argv:
        return
    game = argv[0]
    if game == "life":
        from games.life import solve
    elif game == "sub":
        from games.sub import solve
    elif game == "nim":
        from games.nim import solve
    elif game == "wythoff":
        from games.wythoff import solve
    else:
        return
    text = sys.stdin.read()
    out = solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
