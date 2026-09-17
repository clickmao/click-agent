"""CLI 入口: python3 -m toolkit <vm|jsonmini>.

从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出.
stderr 静默, 不打印任何多余文字.
"""
import sys


def main():
    try:
        if len(sys.argv) != 2:
            return 0
        cmd = sys.argv[1]
        if cmd == "vm":
            from . import vm as mod
        elif cmd == "jsonmini":
            from . import jsonmini as mod
        else:
            return 0
        data = sys.stdin.read()
        out = mod.solve(data)
        sys.stdout.write(out)
    except Exception:
        # 静默失败
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
