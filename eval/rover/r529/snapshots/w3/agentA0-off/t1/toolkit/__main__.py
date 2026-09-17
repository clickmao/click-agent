"""CLI 入口: python3 -m toolkit <vm|jsonmini>

从标准输入读取全部文本, 调用对应模块的 solve, 将返回值写到标准输出。
stderr 保持静默 (不打印任何多余文字)。
"""
import sys

from . import vm, jsonmini

_MODULES = {"vm": vm, "jsonmini": jsonmini}


def main(argv):
    if len(argv) != 1 or argv[0] not in _MODULES:
        return 2
    text = sys.stdin.read()
    out = _MODULES[argv[0]].solve(text)
    sys.stdout.write(out)
    sys.stdout.write("\n" if out else "")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
