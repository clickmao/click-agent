"""CLI entry: python3 -m games <game_id> reads stdin, writes solve() output."""

import sys


def main(argv):
    if len(argv) < 2:
        return 1
    game = argv[1]
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
    text = sys.stdin.read()
    sys.stdout.write(solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
