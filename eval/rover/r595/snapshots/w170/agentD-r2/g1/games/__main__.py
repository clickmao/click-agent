import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    gid = sys.argv[1]
    text = sys.stdin.read()
    out = _MODULES[gid].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
