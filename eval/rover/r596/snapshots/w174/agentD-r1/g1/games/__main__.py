import sys
from games import life, sub, nim, wythoff

MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    if len(sys.argv) < 2:
        return
    gid = sys.argv[1]
    if gid not in MODULES:
        return
    text = sys.stdin.read()
    out = MODULES[gid].solve(text)
    sys.stdout.write(out + '\n')


if __name__ == '__main__':
    main()
