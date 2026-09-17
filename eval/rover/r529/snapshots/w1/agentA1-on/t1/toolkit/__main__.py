"""CLI 入口: python3 -m toolkit <vm|jsonmini>

从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出。
不打印任何多余文字 (stderr 亦静默)。
"""
import sys

_MODULES = {
    "vm": "toolkit.vm",
    "jsonmini": "toolkit.jsonmini",
}


def main(argv):
    if len(argv) != 2 or argv[1] not in _MODULES:
        return 2
    name = _MODULES[argv[1]]
    mod = __import__(name, fromlist=["solve"])
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
