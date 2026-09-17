import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game_id = sys.argv[1]
    module = _MODULES[game_id]
    text = sys.stdin.read()
    out = module.solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
