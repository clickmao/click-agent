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
    sys.stdout.write(MODULES[game].solve(data))

if __name__ == '__main__':
    main()
