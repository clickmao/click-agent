import sys

from . import life as life_mod
from . import sub as sub_mod
from . import nim as nim_mod
from . import wythoff as wythoff_mod

MODULES = {
    'life': life_mod,
    'sub': sub_mod,
    'nim': nim_mod,
    'wythoff': wythoff_mod,
}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    out = MODULES[game_id].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
