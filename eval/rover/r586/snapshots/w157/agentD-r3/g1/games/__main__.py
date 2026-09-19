"""CLI 入口：python3 -m games <game_id>，从 stdin 读全文，输出 solve 结果。"""
import sys


def main():
    game = sys.argv[1]
    mod = __import__('games.' + game, fromlist=['solve'])
    data = sys.stdin.read()
    sys.stdout.write(mod.solve(data))


main()
