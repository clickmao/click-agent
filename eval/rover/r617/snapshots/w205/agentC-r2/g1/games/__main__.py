"""CLI 入口: python3 -m games <game_id>, game_id in {life, sub, nim, wythoff}。

从标准输入读取全部文本, 调用对应模块的 solve, 把返回值写到标准输出 (末尾即 solve 返回值, 由其自身决定)。
"""

import sys


def main():
    if len(sys.argv) < 2:
        return 2
    game_id = sys.argv[1]
    text = sys.stdin.read()

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

    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main())
