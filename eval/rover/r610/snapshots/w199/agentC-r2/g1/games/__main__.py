"""CLI entry: python3 -m games <game_id>"""
import sys


def main():
    argv = sys.argv[1:]
    if not argv:
        return
    game_id = argv[0]
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

    text = sys.stdin.read()
    out = solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
