"""CLI: python3 -m games <game_id> < stdin。"""
import sys


def main():
    if len(sys.argv) < 2:
        return
    game = sys.argv[1]
    mod = __import__('games.' + game, fromlist=['solve'])
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main()
