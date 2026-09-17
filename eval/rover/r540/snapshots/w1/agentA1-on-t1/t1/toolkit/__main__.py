"""CLI 入口: python3 -m toolkit <vm|jsonmini>

从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出。
stderr 静默。
"""

import sys


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in ("vm", "jsonmini"):
        return 2
    name = args[0]
    data = sys.stdin.buffer.read()
    text = data.decode("utf-8")
    if name == "vm":
        from . import vm as mod
    else:
        from . import jsonmini as mod
    result = mod.solve(text)
    sys.stdout.buffer.write(result.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
