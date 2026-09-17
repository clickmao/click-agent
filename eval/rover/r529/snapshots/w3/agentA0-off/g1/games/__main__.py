"""CLI 入口: python3 -m games <game_id>

从标准输入读取全部文本, 调用对应游戏的 solve, 把返回值 (末尾不带换行)
写到标准输出。不打印任何多余文字; 出错时静默退出 (非 0)。
"""

import sys


def main(argv):
    if len(argv) != 2:
        return 2
    game_id = argv[1]
    if game_id == "life":
        from . import life as mod
    elif game_id == "sub":
        from . import sub as mod
    elif game_id == "nim":
        from . import nim as mod
    elif game_id == "wythoff":
        from . import wythoff as mod
    else:
        return 2

    data = sys.stdin.read()
    try:
        out = mod.solve(data)
    except Exception:
        return 1
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
