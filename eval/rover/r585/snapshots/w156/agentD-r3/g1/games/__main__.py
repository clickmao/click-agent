import sys

from . import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    argv = sys.argv[1:]
    if len(argv) != 1 or argv[0] not in MODULES:
        return
    text = sys.stdin.read()
    out = MODULES[argv[0]].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
