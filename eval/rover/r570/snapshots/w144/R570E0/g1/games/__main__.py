"""CLI 入口: python3 -m games <game_id>"""

import sys

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in _MODULES:
        return
    module = _MODULES[sys.argv[1]]
    text = sys.stdin.read()
    sys.stdout.write(module.solve(text))


if __name__ == '__main__':
    main()
