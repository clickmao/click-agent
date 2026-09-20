"""CLI 入口: python3 -m games <game_id> 从 stdin 读取全部文本, 调用对应模块的 solve 并写出结果。"""

import sys

from games import life, nim, sub, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in MODULES:
        return 1
    text = sys.stdin.read()
    out = MODULES[sys.argv[1]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
