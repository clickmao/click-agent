import sys
from . import life, sub, nim, wythoff

def main():
    game = sys.argv[1]
    text = sys.stdin.read()
    if text.endswith('\n'):
        text = text[:-1]
    mod = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}[game]
    sys.stdout.write(mod.solve(text))

if __name__ == '__main__':
    main()
