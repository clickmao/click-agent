import sys

MODULES = ('life', 'sub', 'nim', 'wythoff')


def main():
    game = sys.argv[1]
    if game not in MODULES:
        return 1
    text = sys.stdin.read()
    mod = __import__('games.' + game, fromlist=['solve'])
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
