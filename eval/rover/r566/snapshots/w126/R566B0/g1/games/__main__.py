import sys

from games import life, sub, nim, wythoff

MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in MODULES:
        return
    text = sys.stdin.read()
    sys.stdout.write(MODULES[args[0]].solve(text))


if __name__ == '__main__':
    main()
