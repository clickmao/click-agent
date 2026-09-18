import sys

from . import life, sub, nim, wythoff

_SOLVERS = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    fn = _SOLVERS.get(sys.argv[1])
    if fn is None:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(fn(text))
    return 0


if __name__ == '__main__':
    sys.exit(main())
