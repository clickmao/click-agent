"""CLI 入口: python3 -m games <game_id>  (life|sub|nim|wythoff)。

从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出。
stderr 保持静默。
"""
import sys

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> int:
    game_id = sys.argv[1] if len(sys.argv) > 1 else ''
    mod = _MODULES.get(game_id)
    if mod is None:
        return 2
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
