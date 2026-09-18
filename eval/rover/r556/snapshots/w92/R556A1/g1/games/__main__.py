import sys


def main():
    game = sys.argv[1]
    text = sys.stdin.read()
    if game == 'life':
        from games import life as mod
    elif game == 'sub':
        from games import sub as mod
    elif game == 'nim':
        from games import nim as mod
    elif game == 'wythoff':
        from games import wythoff as mod
    else:
        sys.exit(1)
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main()
