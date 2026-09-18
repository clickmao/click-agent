"""CLI 入口: python3 -m games <game_id>"""
import sys


def main():
    game = sys.argv[1]
    text = sys.stdin.read()
    mod = __import__('games.' + game, fromlist=['solve'])
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
