"""CLI 入口: python3 -m games <life|sub|nim|wythoff>

从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出。
只用标准库; 不打印任何多余文字 (stderr 亦静默)。
"""
import sys

# 显式映射, 避免 importlib 动态导入 (AOT/静态友好)
from games import life, sub, nim, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in _GAMES:
        return 2
    data = sys.stdin.read()
    out = _GAMES[argv[0]](data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
