import sys
import importlib

sys.dont_write_bytecode = True


def main():
    game = sys.argv[1]
    text = sys.stdin.read()
    mod = importlib.import_module('games.' + game)
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
