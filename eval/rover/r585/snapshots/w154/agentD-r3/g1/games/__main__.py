import sys

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    argv = sys.argv[1:]
    if len(argv) != 1 or argv[0] not in _MODULES:
        return
    text = sys.stdin.read()
    out = _MODULES[argv[0]].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
