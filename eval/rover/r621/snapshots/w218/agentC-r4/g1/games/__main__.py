"""CLI 入口: python3 -m games <game_id> [< stdinput]。

从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出。
全程静默 stderr。
"""
import sys


def main(argv):
    if len(argv) != 1:
        return 2
    name = argv[0]
    if name == "life":
        from . import life as mod
    elif name == "sub":
        from . import sub as mod
    elif name == "nim":
        from . import nim as mod
    elif name == "wythoff":
        from . import wythoff as mod
    else:
        return 2
    data = sys.stdin.read()
    sys.stdout.write(mod.solve(data))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
