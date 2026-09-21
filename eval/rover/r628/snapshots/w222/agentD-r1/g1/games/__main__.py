import sys
from . import life, sub, nim, wythoff


def main():
    game = sys.argv[1]
    mod = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}[game]
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)


main()
