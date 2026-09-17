"""games CLI 入口。

用法:
    python3 -m games <game_id>

<game_id> 取 life / sub / nim / wythoff。
从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出。
"""

import sys

from games import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in _MODULES:
        return 2
    text = sys.stdin.read()
    out = _MODULES[argv[1]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
