import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from games import life, sub, nim, wythoff

MODS = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    gid = sys.argv[1] if len(sys.argv) > 1 else ''
    mod = MODS.get(gid)
    if mod is None:
        return
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main()
