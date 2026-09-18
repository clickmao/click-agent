import sys

from . import life, sub, nim, wythoff

GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}

if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] in GAMES:
        out = GAMES[sys.argv[1]](sys.stdin.read())
        if out:
            sys.stdout.write(out)
