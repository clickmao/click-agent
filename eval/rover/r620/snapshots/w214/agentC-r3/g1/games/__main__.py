"""CLI 入口: python3 -m games <game_id>, 从 stdin 读取全部文本并写出 solve 的返回值。"""
import sys
import os


def main():
    argv = sys.argv[1:]
    if not argv:
        return
    game_id = argv[0]
    if game_id == 'life':
        from . import life as mod
    elif game_id == 'sub':
        from . import sub as mod
    elif game_id == 'nim':
        from . import nim as mod
    elif game_id == 'wythoff':
        from . import wythoff as mod
    else:
        return
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main()
