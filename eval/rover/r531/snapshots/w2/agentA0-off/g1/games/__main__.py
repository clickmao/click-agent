"""CLI 入口: python3 -m games <game_id>

<game_id> 取 life/sub/nim/wythoff 之一。
从标准输入读取全部文本, 调用对应模块的 solve(), 把返回值写到标准输出。
不打印任何多余文字 (stderr 亦须静默)。
"""

import sys

from . import life, sub, nim, wythoff

_REGISTRY = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in _REGISTRY:
        return 2
    text = sys.stdin.read()
    out = _REGISTRY[argv[1]](text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
