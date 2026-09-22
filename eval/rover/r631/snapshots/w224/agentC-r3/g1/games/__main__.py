import sys

from . import life, nim, sub, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}

def main() -> None:
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in _MODULES:
        sys.exit(1)
    text = sys.stdin.read()
    out = _MODULES[args[0]].solve(text)
    sys.stdout.write(out)

if __name__ == '__main__':
    main()
