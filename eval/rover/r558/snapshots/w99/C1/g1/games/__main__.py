import sys
from importlib import import_module


def main():
    if len(sys.argv) < 2:
        return
    game = sys.argv[1]
    text = sys.stdin.read()
    mod = import_module('games.' + game)
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main()
