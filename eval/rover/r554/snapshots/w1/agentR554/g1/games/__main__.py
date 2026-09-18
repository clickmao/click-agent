import sys

from games import life, nim, sub, wythoff

MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ''
    mod = MODULES.get(arg)
    if mod is None:
        return
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
