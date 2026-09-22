"""CLI 入口: python3 -m games <game_id>

从标准输入读取全部文本，调用对应模块的 solve，
把返回值原样写到标准输出（不加任何多余字符）。
"""

import sys


def main() -> int:
    args = sys.argv[1:]
    if not args:
        return 2
    game_id = args[0]
    if game_id == 'life':
        from games import life as mod
    elif game_id == 'sub':
        from games import sub as mod
    elif game_id == 'nim':
        from games import nim as mod
    elif game_id == 'wythoff':
        from games import wythoff as mod
    else:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main())
