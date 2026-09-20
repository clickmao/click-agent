import sys
import importlib


def main():
    game = sys.argv[1]
    mod = importlib.import_module('games.' + game)
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
