"""CLI 入口: python3 -m games <game_id>，game_id ∈ life/sub/nim/wythoff。"""

import sys

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    game = sys.argv[1]
    mod = _MODULES.get(game)
    if mod is None:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main())
