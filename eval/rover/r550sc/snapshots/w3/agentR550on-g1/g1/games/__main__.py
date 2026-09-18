import sys

import games.life
import games.sub
import games.nim
import games.wythoff

_MODULES = {
    'life': games.life,
    'sub': games.sub,
    'nim': games.nim,
    'wythoff': games.wythoff,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in _MODULES:
        return 0
    text = sys.stdin.read()
    out = _MODULES[argv[1]].solve(text)
    if out:
        sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
