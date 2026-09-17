import sys

from games import life, sub, nim, wythoff

MODULES = {'life': life, 'sub': sub, 'nim': nim, 'wythoff': wythoff}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    mod = MODULES[game_id]
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
