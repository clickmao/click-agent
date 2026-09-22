"""CLI 入口: python3 -m games <game_id>

game_id 取 life/sub/nim/wythoff; 从 stdin 读全部文本, 调 solve, 写 stdout。
"""

import sys

from . import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _MODULES:
        return 1
    text = sys.stdin.read()
    result = _MODULES[argv[0]].solve(text)
    sys.stdout.write(result)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
