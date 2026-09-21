"""CLI 入口: python3 -m games <game_id>。"""

import sys


def main(argv):
    if len(argv) != 1:
        return 1
    game = argv[0]
    if game == 'life':
        from .life import solve
    elif game == 'sub':
        from .sub import solve
    elif game == 'nim':
        from .nim import solve
    elif game == 'wythoff':
        from .wythoff import solve
    else:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
