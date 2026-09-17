"""CLI 入口: python3 -m games <game_id>  (game_id ∈ life/sub/nim/wythoff)。

从 stdin 读全部文本, 调用对应模块的 solve, 将返回值写入 stdout（无多余输出）。
"""

import sys

from games.life import solve as life_solve
from games.sub import solve as sub_solve
from games.nim import solve as nim_solve
from games.wythoff import solve as wythoff_solve

_SOLVERS = {
    'life': life_solve,
    'sub': sub_solve,
    'nim': nim_solve,
    'wythoff': wythoff_solve,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _SOLVERS:
        return 2
    text = sys.stdin.read()
    out = _SOLVERS[argv[0]](text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
