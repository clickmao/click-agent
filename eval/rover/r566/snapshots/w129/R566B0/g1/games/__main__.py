import sys
from . import life, sub, nim, wythoff

TARGETS = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}

def main():
    game = sys.argv[1]
    text = sys.stdin.read()
    out = TARGETS[game].solve(text)
    sys.stdout.write(out)

if __name__ == '__main__':
    main()
