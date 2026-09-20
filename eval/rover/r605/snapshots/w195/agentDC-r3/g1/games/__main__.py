import sys

from . import life, sub, nim, wythoff

_MODS = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    gid = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(_MODS[gid].solve(text))


if __name__ == '__main__':
    main()
