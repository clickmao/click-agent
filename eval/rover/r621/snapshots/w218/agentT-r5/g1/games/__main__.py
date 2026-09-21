"""CLI entry point: python3 -m games <game_id>."""

import sys


def main() -> None:
    game = sys.argv[1]
    text = sys.stdin.read()
    if game == 'life':
        from games.life import solve
    elif game == 'sub':
        from games.sub import solve
    elif game == 'nim':
        from games.nim import solve
    else:
        from games.wythoff import solve
    sys.stdout.write(solve(text))


if __name__ == '__main__':
    main()
