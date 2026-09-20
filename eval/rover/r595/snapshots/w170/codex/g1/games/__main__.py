import sys

from . import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in MODULES:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(MODULES[sys.argv[1]].solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main())
