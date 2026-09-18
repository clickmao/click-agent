import sys


def main():
    game = sys.argv[1]
    if game == 'life':
        from . import life as mod
    elif game == 'sub':
        from . import sub as mod
    elif game == 'nim':
        from . import nim as mod
    else:
        from . import wythoff as mod
    data = sys.stdin.read()
    sys.stdout.write(mod.solve(data))


if __name__ == '__main__':
    main()
