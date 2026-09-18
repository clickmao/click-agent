import sys


def main():
    if len(sys.argv) < 2:
        return
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
        return
    out = solve(data)
    if out != '':
        sys.stdout.write(out + '\n')


if __name__ == '__main__':
    main()
