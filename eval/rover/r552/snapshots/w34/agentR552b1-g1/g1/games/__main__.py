import sys


def main(argv):
    if len(argv) != 2:
        return
    game = argv[1]
    mod = None
    if game == 'life':
        from games import life as mod
    elif game == 'sub':
        from games import sub as mod
    elif game == 'nim':
        from games import nim as mod
    elif game == 'wythoff':
        from games import wythoff as mod
    else:
        return
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main(sys.argv)
