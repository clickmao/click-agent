"""CLI 入口: python3 -m games <game_id>

从 stdin 读全部文本, 调用对应模块的 solve, 把返回值写到 stdout。
"""

import sys

from games import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] not in _MODULES:
        return 1
    text = sys.stdin.read()
    out = _MODULES[args[0]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
