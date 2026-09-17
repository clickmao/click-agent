import sys

from . import life, nim, sub, wythoff

GAMES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main(argv):
    if len(argv) != 2 or argv[1] not in GAMES:
        return 0
    text = sys.stdin.read()
    out = GAMES[argv[1]].solve(text)
    if out:
        sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
