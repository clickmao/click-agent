"""CLI 入口: python3 -m games <game_id>

<game_id> 取 life/sub/nim/wythoff。
从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出。
不得打印任何多余文字(stdout 只含 solve 的返回值, stderr 静默)。
"""

import sys

from . import life, nim, sub, wythoff


MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    game_id = argv[1] if len(argv) > 1 else ""
    mod = MODULES.get(game_id)
    if mod is None:
        return 2
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
