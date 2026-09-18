import sys

if __name__ == '__main__':
    argv = sys.argv[1:]
    if not argv:
        sys.exit(1)
    gid = argv[0]
    text = sys.stdin.read()
    if gid == 'life':
        from games.life import solve
    elif gid == 'sub':
        from games.sub import solve
    elif gid == 'nim':
        from games.nim import solve
    elif gid == 'wythoff':
        from games.wythoff import solve
    else:
        sys.exit(1)
    out = solve(text)
    sys.stdout.write(out)
