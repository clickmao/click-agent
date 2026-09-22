"""CLI 入口: python3 -m games <game_id>, game_id ∈ {life, sub, nim, wythoff}。

从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出。
"""

import sys


def main(argv):
    if len(argv) < 2:
        return 1
    game_id = argv[1]
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

    text = sys.stdin.read()
    out = solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
