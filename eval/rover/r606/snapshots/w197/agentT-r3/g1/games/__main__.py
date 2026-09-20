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


def main() -> None:
    if len(sys.argv) < 2:
        return
    module = _MODULES.get(sys.argv[1])
    if module is None:
        return
    text = sys.stdin.read()
    sys.stdout.write(module.solve(text))


if __name__ == '__main__':
    main()
