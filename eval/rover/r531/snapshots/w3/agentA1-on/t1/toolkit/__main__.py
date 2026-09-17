"""CLI 入口: python3 -m toolkit <vm|jsonmini>

从标准输入读全部文本 -> 对应模块 solve -> 写标准输出(不额外加换行).
"""

import sys


def main(argv):
    if len(argv) != 2 or argv[1] not in ("vm", "jsonmini"):
        sys.stdout.write("ERR")
        return 1
    name = argv[1]
    if name == "vm":
        from . import vm as mod
    else:
        from . import jsonmini as mod
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
