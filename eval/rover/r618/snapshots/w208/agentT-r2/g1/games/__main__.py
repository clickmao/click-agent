import sys


def main():
    args = sys.argv[1:]
    if not args:
        return
    gid = args[0]
    if gid == 'life':
        from games.life import solve
    elif gid == 'sub':
        from games.sub import solve
    elif gid == 'nim':
        from games.nim import solve
    elif gid == 'wythoff':
        from games.wythoff import solve
    else:
        return
    text = sys.stdin.read()
    out = solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
