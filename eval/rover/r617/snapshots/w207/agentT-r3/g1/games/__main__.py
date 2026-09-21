"""CLI 入口：python3 -m games <life|sub|nim|wythoff>。"""

import sys


def main():
    game_id = sys.argv[1]
    data = sys.stdin.read()
    if game_id == 'life':
        from .life import solve
    elif game_id == 'sub':
        from .sub import solve
    elif game_id == 'nim':
        from .nim import solve
    elif game_id == 'wythoff':
        from .wythoff import solve
    else:
        return
    sys.stdout.write(solve(data))


if __name__ == '__main__':
    main()
