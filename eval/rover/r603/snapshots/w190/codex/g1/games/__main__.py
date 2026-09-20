import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> None:
    game_id = sys.argv[1] if len(sys.argv) > 1 else ''
    module = _MODULES.get(game_id)
    if module is None:
        return
    sys.stdout.write(module.solve(sys.stdin.read()))


if __name__ == '__main__':
    main()
