import sys

from . import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    mod = MODULES[sys.argv[1]]
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)


main()
