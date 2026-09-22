import importlib
import sys


def main():
    if len(sys.argv) < 2:
        return
    game_id = sys.argv[1]
    if game_id not in ('life', 'sub', 'nim', 'wythoff'):
        return
    mod = importlib.import_module('games.' + game_id)
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
