"""CLI entry point: python3 -m games <game_id> ; reads stdin, writes stdout."""
import sys


def main() -> None:
    if len(sys.argv) < 2:
        return
    game_id = sys.argv[1]
    if game_id == 'life':
        from games.life import solve
    elif game_id == 'sub':
        from games.sub import solve
    elif game_id == 'nim':
        from games.nim import solve
    elif game_id == 'wythoff':
        from games.wythoff import solve
    else:
        return
    text = sys.stdin.read()
    sys.stdout.write(solve(text))


if __name__ == '__main__':
    main()
