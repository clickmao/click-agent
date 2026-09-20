"""CLI entry: python3 -m games <game_id>."""

import sys


def main():
    game = sys.argv[1]
    data = sys.stdin.read()
    if game == 'life':
        from games import life as mod
    elif game == 'sub':
        from games import sub as mod
    elif game == 'nim':
        from games import nim as mod
    elif game == 'wythoff':
        from games import wythoff as mod
    else:
        return
    out = mod.solve(data)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
