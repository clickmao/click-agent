"""CLI 入口: python3 -m toolkit <vm|jsonmini>

从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出。
静默: 不打印任何多余文字 (含 stderr)。
"""
import sys


def main(argv):
    if len(argv) != 1:
        return 2
    name = argv[0]
    if name in ("vm", "vm_run"):
        from toolkit import vm as mod
    elif name in ("jsonmini", "json_mini"):
        from toolkit import jsonmini as mod
    else:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
