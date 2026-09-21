"""CLI 入口: python3 -m games <game_id>

<game_id> 取 life/sub/nim/wythoff。从标准输入读全部文本,
调用对应模块的 solve, 把返回值写到标准输出 (末尾不加换行)。
"""

import sys

from . import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv) -> int:
    if len(argv) != 2 or argv[1] not in _MODULES:
        return 1
    text = sys.stdin.read()
    out = _MODULES[argv[1]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
