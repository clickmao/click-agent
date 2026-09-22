"""CLI 入口：python3 -m games <game_id>，stdin 全文交给对应 solve，输出其返回值。"""

import sys


def main() -> None:
    argv = sys.argv[1:]
    if not argv:
        return
    game_id = argv[0]
    text = sys.stdin.read()
    if game_id == "life":
        from .life import solve
    elif game_id == "sub":
        from .sub import solve
    elif game_id == "nim":
        from .nim import solve
    elif game_id == "wythoff":
        from .wythoff import solve
    else:
        return
    sys.stdout.write(solve(text))


if __name__ == "__main__":
    main()
