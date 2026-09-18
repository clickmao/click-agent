"""CLI 入口: python3 -m games <game_id>。

从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出。
"""

import sys
import io

from games import life as life_mod
from games import sub as sub_mod
from games import nim as nim_mod
from games import wythoff as wythoff_mod

GAMES = {
    "life": life_mod,
    "sub": sub_mod,
    "nim": nim_mod,
    "wythoff": wythoff_mod,
}


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] not in GAMES:
        return 1
    mod = GAMES[argv[0]]
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
