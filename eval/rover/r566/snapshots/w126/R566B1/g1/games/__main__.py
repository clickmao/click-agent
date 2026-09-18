import sys

from games import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    if len(sys.argv) < 2:
        return
    mod = MODULES.get(sys.argv[1])
    if mod is None:
        return
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
