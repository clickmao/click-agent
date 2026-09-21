import sys
from . import life, sub, nim, wythoff

MODS = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    gid = sys.argv[1]
    data = sys.stdin.read()
    out = MODS[gid].solve(data)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
