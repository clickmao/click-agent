"""CLI entry: python3 -m games <game_id> reads stdin, writes solve() output."""
import sys


def main() -> None:
    game = sys.argv[1]
    data = sys.stdin.read()
    if game == 'life':
        from games.life import solve
    elif game == 'sub':
        from games.sub import solve
    elif game == 'nim':
        from games.nim import solve
    elif game == 'wythoff':
        from games.wythoff import solve
    else:
        return
    sys.stdout.write(solve(data))


if __name__ == '__main__':
    main()
