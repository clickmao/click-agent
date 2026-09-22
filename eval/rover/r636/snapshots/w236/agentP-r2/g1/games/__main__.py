"""CLI entry point: python3 -m games <game_id>"""
import sys


def main():
    argv = sys.argv[1:]
    if len(argv) != 1:
        return
    game_id = argv[0]
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
        return
    out = solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
