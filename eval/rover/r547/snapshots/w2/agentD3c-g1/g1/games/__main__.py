import sys

from . import life, sub, nim, wythoff

MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] not in MODULES:
        sys.exit(1)
    text = sys.stdin.read()
    out = MODULES[argv[0]].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
