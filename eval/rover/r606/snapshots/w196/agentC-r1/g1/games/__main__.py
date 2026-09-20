import sys

from . import life, sub, nim, wythoff

MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    if len(sys.argv) < 2:
        return
    mod = MODULES.get(sys.argv[1])
    if mod is None:
        return
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main()
