"""CLI entry: python3 -m games <game_id>"""
import sys


def main():
    args = sys.argv[1:]
    if not args:
        return 1
    gid = args[0]
    text = sys.stdin.read()
    if gid == 'life':
        from games import life as mod
    elif gid == 'sub':
        from games import sub as mod
    elif gid == 'nim':
        from games import nim as mod
    elif gid == 'wythoff':
        from games import wythoff as mod
    else:
        return 1
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
