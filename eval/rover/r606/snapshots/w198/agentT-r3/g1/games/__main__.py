import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> None:
    game_id = sys.argv[1]
    mod = _MODULES[game_id]
    sys.stdout.write(mod.solve(sys.stdin.read()))


if __name__ == '__main__':
    main()
