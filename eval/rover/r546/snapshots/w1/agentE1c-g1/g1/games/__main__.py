import sys

from . import life as _life
from . import sub as _sub
from . import nim as _nim
from . import wythoff as _wythoff

MODULES = {
    'life': _life,
    'sub': _sub,
    'nim': _nim,
    'wythoff': _wythoff,
}


def main(argv):
    game_id = argv[1] if len(argv) > 1 else ''
    text = sys.stdin.read()
    out = MODULES[game_id].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main(sys.argv)
