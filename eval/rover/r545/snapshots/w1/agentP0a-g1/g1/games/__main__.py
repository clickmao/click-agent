import sys
import importlib


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    mod = importlib.import_module('games.' + game_id)
    out = mod.solve(text)
    if out:
        sys.stdout.write(out)


main()
