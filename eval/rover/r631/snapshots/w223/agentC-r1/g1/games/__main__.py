"""CLI 入口：python3 -m games <game_id>。

从标准输入读取全部文本，调用对应模块的 solve，把返回值写到标准输出。
"""

import sys

from games import life, sub, nim, wythoff

GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in GAMES:
        return
    text = sys.stdin.read()
    out = GAMES[sys.argv[1]].solve(text)
    sys.stdout.write(out + '\n')


if __name__ == '__main__':
    main()
