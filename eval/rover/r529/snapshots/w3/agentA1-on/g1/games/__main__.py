"""CLI 入口: python3 -m games <game_id>

从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出 (末尾不带换行)。
"""
import sys


def main() -> int:
    if len(sys.argv) < 2:
        return 2
    game_id = sys.argv[1]
    if game_id == "life":
        from games import life as mod
    elif game_id == "sub":
        from games import sub as mod
    elif game_id == "nim":
        from games import nim as mod
    elif game_id == "wythoff":
        from games import wythoff as mod
    else:
        return 2

    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
