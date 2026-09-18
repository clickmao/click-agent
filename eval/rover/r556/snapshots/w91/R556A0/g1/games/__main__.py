import sys


def main():
    args = sys.argv[1:]
    game = args[0]
    text = sys.stdin.read()
    if game == 'life':
        from . import life as mod
    elif game == 'sub':
        from . import sub as mod
    elif game == 'nim':
        from . import nim as mod
    elif game == 'wythoff':
        from . import wythoff as mod
    else:
        return
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
