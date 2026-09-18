"""CLI 入口: python3 -m games <game_id>，stdin -> solve -> stdout（无多余输出）。"""

import sys


def main():
    game_id = sys.argv[1]
    mod = __import__('games.' + game_id, fromlist=[game_id])
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main()
