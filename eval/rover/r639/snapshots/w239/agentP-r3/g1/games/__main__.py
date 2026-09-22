"""CLI 入口：python3 -m games <game_id>（game_id 取 life/sub/nim/wythoff）。

从标准输入读取全部文本，调用对应模块的 solve，把返回值写到标准输出。
静默：不打印任何多余文字或提示，stderr 亦保持静默。
"""

import sys

from games import life, nim, sub, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in _MODULES:
        return
    text = sys.stdin.read()
    sys.stdout.write(_MODULES[sys.argv[1]].solve(text))


if __name__ == '__main__':
    main()
