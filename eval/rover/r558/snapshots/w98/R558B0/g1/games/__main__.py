import sys

from . import life, nim, sub, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(MODULES[game].solve(text))


if __name__ == '__main__':
    main()
