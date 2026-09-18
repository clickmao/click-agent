"""CLI 入口: python3 -m games <game_id>

<game_id> 取 life/sub/nim/wythoff。
从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出。
"""

import sys

from games import life, nim, sub, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    if len(argv) != 1:
        return 2
    mod = _MODULES.get(argv[0])
    if mod is None:
        return 2
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
