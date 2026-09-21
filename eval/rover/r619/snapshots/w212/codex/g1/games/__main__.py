import sys

from . import life, nim, sub, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in MODULES:
        return
    text = sys.stdin.read()
    sys.stdout.write(MODULES[sys.argv[1]].solve(text))


if __name__ == '__main__':
    main()
