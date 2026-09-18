"""CLI 入口: python3 -m games <game_id>"""
import sys


def main():
    game = sys.argv[1]
    data = sys.stdin.read()
    if game == 'life':
        from . import life as mod
    elif game == 'sub':
        from . import sub as mod
    elif game == 'nim':
        from . import nim as mod
    elif game == 'wythoff':
        from . import wythoff as mod
    else:
        return
    out = mod.solve(data)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
