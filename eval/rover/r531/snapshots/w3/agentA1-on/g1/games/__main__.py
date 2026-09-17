"""CLI 入口: python3 -m games <game_id>

从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出。
stderr 静默: 任何异常都不打印, 仅以非零退出码表示失败。
"""

import sys


def main(argv):
    if len(argv) != 2:
        return 2
    game_id = argv[1]
    try:
        if game_id == 'life':
            from . import life as mod
        elif game_id == 'sub':
            from . import sub as mod
        elif game_id == 'nim':
            from . import nim as mod
        elif game_id == 'wythoff':
            from . import wythoff as mod
        else:
            return 2
        raw = sys.stdin.read()
        out = mod.solve(raw)
        sys.stdout.write(out)
        return 0
    except Exception:
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
