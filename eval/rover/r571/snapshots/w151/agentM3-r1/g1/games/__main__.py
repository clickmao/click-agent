"""CLI entry: python3 -m games <life|sub|nim|wythoff>"""
import sys

from . import life
from . import sub
from . import nim
from . import wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    game_id = argv[1]
    mod = MODULES[game_id]
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main(sys.argv)
