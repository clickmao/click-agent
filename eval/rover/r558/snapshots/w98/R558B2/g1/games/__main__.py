import sys


def main():
    game = sys.argv[1]
    data = sys.stdin.read()
    if game == 'life':
        from .life import solve
    elif game == 'sub':
        from .sub import solve
    elif game == 'nim':
        from .nim import solve
    elif game == 'wythoff':
        from .wythoff import solve
    else:
        return
    sys.stdout.write(solve(data))


if __name__ == '__main__':
    main()
