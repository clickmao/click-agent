import sys
from . import life, sub, nim, wythoff

def main():
    game = sys.argv[1]
    data = sys.stdin.read()
    mod = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}[game]
    out = mod.solve(data)
    sys.stdout.write(out)

if __name__ == '__main__':
    main()
