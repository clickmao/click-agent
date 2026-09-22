"""CLI 入口: python3 -m games <game_id>"""
import sys


def main() -> None:
    argv = sys.argv[1:]
    if len(argv) != 1:
        return
    game = argv[0]
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
    data = sys.stdin.read()
    out = solve(data)
    if out:
        sys.stdout.write(out + '\n')


if __name__ == '__main__':
    main()
