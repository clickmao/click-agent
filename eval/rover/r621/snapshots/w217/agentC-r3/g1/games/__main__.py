import sys

from games import life as _life
from games import sub as _sub
from games import nim as _nim
from games import wythoff as _wythoff

_MODULES = {
    'life': _life,
    'sub': _sub,
    'nim': _nim,
    'wythoff': _wythoff,
}


def main():
    if len(sys.argv) != 2:
        return 1
    mod = _MODULES.get(sys.argv[1])
    if mod is None:
        return 1
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
