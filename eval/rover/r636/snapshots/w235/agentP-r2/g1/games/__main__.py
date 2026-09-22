"""CLI 入口: python3 -m games <game_id>。"""
import sys


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    if game_id == 'life':
        from games.life import solve
    elif game_id == 'sub':
        from games.sub import solve
    elif game_id == 'nim':
        from games.nim import solve
    elif game_id == 'wythoff':
        from games.wythoff import solve
    else:
        sys.exit(1)
    sys.stdout.write(solve(text))


if __name__ == '__main__':
    main()
