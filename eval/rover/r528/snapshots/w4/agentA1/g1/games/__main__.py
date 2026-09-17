"""CLI 入口: python3 -m games <game_id>  (game_id: life/sub/nim/wythoff)。

从 stdin 读取全部文本, 调用对应模块的 solve, 把返回值写入 stdout (无额外输出)。
"""
import sys

from . import life, sub, nim, wythoff

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
