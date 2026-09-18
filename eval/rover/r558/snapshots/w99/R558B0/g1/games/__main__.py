"""CLI entry: python3 -m games <game_id>."""

import sys


def main() -> int:
    argv = sys.argv[1:]
    game = argv[0]
    text = sys.stdin.read()
    if game == 'life':
        from games.life import solve
    elif game == 'sub':
        from games.sub import solve
    elif game == 'nim':
        from games.nim import solve
    elif game == 'wythoff':
        from games.wythoff import solve
    else:
        return 1
    out = solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
