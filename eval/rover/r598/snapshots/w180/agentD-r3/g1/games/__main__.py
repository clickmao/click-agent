import sys

from .life import solve as _life
from .sub import solve as _sub
from .nim import solve as _nim
from .wythoff import solve as _wythoff

_GAMES = {'life': _life, 'sub': _sub, 'nim': _nim, 'wythoff': _wythoff}


def main():
    argv = sys.argv
    if len(argv) < 2 or argv[1] not in _GAMES:
        return
    text = sys.stdin.read()
    out = _GAMES[argv[1]](text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
