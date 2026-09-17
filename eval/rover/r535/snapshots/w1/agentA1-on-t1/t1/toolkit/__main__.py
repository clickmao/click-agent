"""CLI 入口: python3 -m toolkit <vm|jsonmini>

从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出。
不打印任何多余文字 (stderr 亦静默)。
"""

import sys


def main() -> int:
    argv = sys.argv[1:]
    if len(argv) != 1:
        return 2
    name = argv[0]
    if name == "vm":
        from . import vm as mod
    elif name == "jsonmini":
        from . import jsonmini as mod
    else:
        return 2

    data = sys.stdin.read()
    result = mod.solve(data)
    sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
