"""CLI 入口: ``python3 -m games <game_id>``。

从标准输入读取全部文本, 调用对应游戏模块的 ``solve``, 把返回值写入标准输出。
<game_id> ∈ {life, sub, nim, wythoff}。

运行示例:
    $ printf '3\\n5 9 4\\n' | python3 -m games nim
    WIN 2 8

约束: 只使用标准库; 不打印任何多余文字 (stderr 亦静默)。
"""

import sys


def main(argv) -> int:
    if len(argv) < 2:
        return 2
    game_id = argv[1]

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
    sys.exit(main(sys.argv))
