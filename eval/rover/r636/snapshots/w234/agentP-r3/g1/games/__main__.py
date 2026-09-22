"""CLI 入口: python3 -m games <game_id> 从 stdin 读全部文本并输出 solve 的结果。"""

import sys

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv) -> None:
    if len(argv) != 1 or argv[0] not in _MODULES:
        return
    text = sys.stdin.read()
    sys.stdout.write(_MODULES[argv[0]].solve(text))


if __name__ == '__main__':
    main(sys.argv[1:])
