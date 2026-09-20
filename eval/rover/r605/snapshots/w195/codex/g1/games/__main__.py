import sys
from . import life, sub, nim, wythoff

GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}

def main():
    if len(sys.argv) < 2:
        return
    fn = GAMES.get(sys.argv[1])
    if fn is None:
        return
    text = sys.stdin.read()
    out = fn(text)
    sys.stdout.write(out)

if __name__ == '__main__':
    main()
