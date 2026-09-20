"""CLI entry: python3 -m games <game_id> reading stdin, writing stdout."""

import sys


def main(argv):
    if len(argv) < 2:
        return 0
    game_id = argv[1]
    if game_id == 'life':
        from games.life import solve
    elif game_id == 'sub':
        from games.sub import solve
    elif game_id == 'nim':
        from games.nim import solve
    elif game_id == 'wythoff':
        from games.wythoff import solve
    else:
        return 0

    text = sys.stdin.read()
    result = solve(text)
    sys.stdout.write(result)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
