import sys
import importlib

MODS = {'life': 'games.life', 'sub': 'games.sub', 'nim': 'games.nim', 'wythoff': 'games.wythoff'}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in MODS:
        return
    mod = importlib.import_module(MODS[sys.argv[1]])
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
