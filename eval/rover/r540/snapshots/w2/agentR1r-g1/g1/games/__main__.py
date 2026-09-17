import sys

from games import life, sub, nim, wythoff

MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    argv = sys.argv
    if len(argv) < 2 or argv[1] not in MODULES:
        return
    sys.stdout.write(MODULES[argv[1]].solve(sys.stdin.read()))


if __name__ == '__main__':
    main()
