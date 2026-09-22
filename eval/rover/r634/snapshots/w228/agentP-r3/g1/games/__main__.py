"""CLI 入口: python3 -m games <game_id>"""
import sys


def main():
    argv = sys.argv[1:]
    if not argv:
        return
    game_id = argv[0]
    if game_id == 'life':
        from games import life as mod
    elif game_id == 'sub':
        from games import sub as mod
    elif game_id == 'nim':
        from games import nim as mod
    elif game_id == 'wythoff':
        from games import wythoff as mod
    else:
        return
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
