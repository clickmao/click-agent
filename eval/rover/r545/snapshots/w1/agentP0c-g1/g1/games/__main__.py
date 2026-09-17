import sys

from . import life, sub, nim, wythoff

MODS = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    data = sys.stdin.read()
    gid = sys.argv[1]
    sys.stdout.write(MODS[gid].solve(data))


if __name__ == '__main__':
    main()
