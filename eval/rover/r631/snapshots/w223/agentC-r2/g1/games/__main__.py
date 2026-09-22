"""CLI 入口: python3 -m games <game_id>, game_id 取 life/sub/nim/wythoff。

从标准输入读取全部文本、调用对应模块的 solve、把返回值写到标准输出。
"""

import sys

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> None:
    game_id = sys.argv[1]
    text = sys.stdin.read()
    out = _MODULES[game_id].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
