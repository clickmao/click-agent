import sys

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game = sys.argv[1]
    text = sys.stdin.read()
    out = _MODULES[game].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
