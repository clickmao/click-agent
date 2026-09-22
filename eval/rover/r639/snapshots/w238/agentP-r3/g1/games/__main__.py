import sys

from games import life as _life
from games import nim as _nim
from games import sub as _sub
from games import wythoff as _wythoff

_MODULES = {
    'life': _life,
    'sub': _sub,
    'nim': _nim,
    'wythoff': _wythoff,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _MODULES:
        return
    text = sys.stdin.read()
    out = _MODULES[argv[0]].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main(sys.argv[1:])
