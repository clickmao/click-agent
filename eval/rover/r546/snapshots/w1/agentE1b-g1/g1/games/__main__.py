import sys
from games import life, sub, nim, wythoff

MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}

def main():
    gid = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(MODULES[gid].solve(text))

if __name__ == '__main__':
    main()
