import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in _MODULES:
        return
    data = sys.stdin.read()
    out = _MODULES[sys.argv[1]].solve(data)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
