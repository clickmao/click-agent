import sys

from games import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    if len(argv) < 2 or argv[1] not in MODULES:
        return 1
    mod = MODULES[argv[1]]
    data = sys.stdin.read()
    sys.stdout.write(mod.solve(data))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
