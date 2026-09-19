import sys

from games import life, sub, nim, wythoff

MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    argv = sys.argv
    if len(argv) != 2 or argv[1] not in MODULES:
        return 1
    text = sys.stdin.read()
    out = MODULES[argv[1]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
