import sys


def main():
    argv = sys.argv[1:]
    if not argv:
        return
    game = argv[0]
    data = sys.stdin.read()
    if game == 'life':
        import games.life as mod
    elif game == 'sub':
        import games.sub as mod
    elif game == 'nim':
        import games.nim as mod
    elif game == 'wythoff':
        import games.wythoff as mod
    else:
        return
    sys.stdout.write(mod.solve(data))


main()
