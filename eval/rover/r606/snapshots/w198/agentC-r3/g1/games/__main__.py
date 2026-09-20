"""CLI entry: python3 -m games <game_id>"""
import sys


def main():
    argv = sys.argv[1:]
    if not argv:
        return
    gid = argv[0]
    text = sys.stdin.read()
    out = ''
    if gid == 'life':
        from games.life import solve as out_fn
        out = out_fn(text)
    elif gid == 'sub':
        from games.sub import solve as out_fn
        out = out_fn(text)
    elif gid == 'nim':
        from games.nim import solve as out_fn
        out = out_fn(text)
    elif gid == 'wythoff':
        from games.wythoff import solve as out_fn
        out = out_fn(text)
    else:
        return
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
