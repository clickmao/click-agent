import sys

from . import life, sub, nim, wythoff

GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    args = sys.argv[1:]
    if not args:
        return
    mod = GAMES.get(args[0])
    if mod is None:
        return
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
