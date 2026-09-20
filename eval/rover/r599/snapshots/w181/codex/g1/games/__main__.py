"""CLI entry point: python3 -m games <game_id>"""

import sys

from games import life, nim, sub, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> None:
    game_id = sys.argv[1]
    data = sys.stdin.read()
    sys.stdout.write(MODULES[game_id].solve(data))


if __name__ == '__main__':
    main()
