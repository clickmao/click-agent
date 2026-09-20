import sys


def main():
    if len(sys.argv) < 2:
        return
    game = sys.argv[1]
    text = sys.stdin.read()
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
    out = solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
