"""CLI 入口：python3 -m games <game_id>，game_id 取 life/sub/nim/wythoff。

从标准输入读取全部文本，调用对应模块的 solve，把返回值写到标准输出（末尾不带换行）。
stderr 保持静默。
"""

import sys


def main() -> int:
    game_id = sys.argv[1] if len(sys.argv) > 1 else ""
    text = sys.stdin.read()
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
    sys.stdout.write(solve(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
