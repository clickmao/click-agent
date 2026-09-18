import sys

from . import life, nim, sub, wythoff

MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main() -> int:
    game = sys.argv[1]
    text = sys.stdin.read()
    out = MODULES[game].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
