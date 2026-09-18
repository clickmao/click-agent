import sys

from . import life, nim, sub, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in _MODULES:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(_MODULES[sys.argv[1]].solve(text))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
