import sys
import importlib


def main():
    game_id = sys.argv[1]
    mod = importlib.import_module('games.' + game_id)
    data = sys.stdin.read()
    sys.stdout.write(mod.solve(data))


if __name__ == '__main__':
    main()
