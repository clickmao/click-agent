import sys

from . import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game = sys.argv[1]
    data = sys.stdin.read()
    out = MODULES[game].solve(data)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
