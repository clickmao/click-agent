import sys

from games import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game = sys.argv[1]
    text = sys.stdin.read()
    out = MODULES[game].solve(text)
    sys.stdout.write(out + '\n')


if __name__ == '__main__':
    main()
