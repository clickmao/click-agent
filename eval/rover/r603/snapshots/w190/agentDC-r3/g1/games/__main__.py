import sys

from . import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    module = MODULES[game_id]
    out = module.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
