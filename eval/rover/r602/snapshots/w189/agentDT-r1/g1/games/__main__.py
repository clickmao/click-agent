import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in _MODULES:
        return
    text = sys.stdin.read()
    out = _MODULES[args[0]].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
