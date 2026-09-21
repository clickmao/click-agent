"""CLI 入口：python3 -m games <game_id>，从 stdin 读全部文本，写 solve 返回值到 stdout。"""

import sys

from games import life, nim, sub, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1 or argv[0] not in MODULES:
        return 2
    mod = MODULES[argv[0]]
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
