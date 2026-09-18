import sys

from games import life, sub, nim, wythoff

MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    args = sys.argv[1:]
    if not args or args[0] not in MODULES:
        return
    text = sys.stdin.read()
    out = MODULES[args[0]].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
