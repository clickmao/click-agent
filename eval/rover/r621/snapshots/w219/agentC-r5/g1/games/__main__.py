"""CLI 入口: python3 -m games <game_id>。

从标准输入读取全部文本、调用对应模块的 solve、把返回值写到标准输出。
"""

import sys

_MODULES = {
    "life": "games.life",
    "sub": "games.sub",
    "nim": "games.nim",
    "wythoff": "games.wythoff",
}


def main():
    game_id = sys.argv[1]
    from importlib import import_module

    module = import_module(_MODULES[game_id])
    text = sys.stdin.read()
    out = module.solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
