import sys


def main():
    game = sys.argv[1]
    data = sys.stdin.read()
    if game == 'life':
        from games.life import solve
    elif game == 'sub':
        from games.sub import solve
    elif game == 'nim':
        from games.nim import solve
    elif game == 'wythoff':
        from games.wythoff import solve
    else:
        sys.exit(1)
    out = solve(data)
    sys.stdout.write(out + '\n')


main()
