import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    if len(sys.argv) != 2:
        return
    game = _MODULES.get(sys.argv[1])
    if game is None:
        return
    sys.stdout.write(game.solve(sys.stdin.read()))


if __name__ == '__main__':
    main()
