import sys

from . import life, sub, nim, wythoff

_SOLVERS = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main(argv):
    text = sys.stdin.read()
    sys.stdout.write(_SOLVERS[argv[1]](text))


if __name__ == '__main__':
    main(sys.argv)
