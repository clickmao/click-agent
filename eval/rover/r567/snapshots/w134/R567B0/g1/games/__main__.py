import sys
import importlib


def main():
    game = sys.argv[1]
    text = sys.stdin.read()
    mod = importlib.import_module('games.' + game)
    sys.stdout.write(mod.solve(text))


main()
