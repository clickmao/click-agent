"""CLI：python3 -m games <game_id>，从 stdin 读全部文本，输出 solve 的返回值。"""

import sys

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    if not argv:
        return 1
    mod = _MODULES.get(argv[0])
    if mod is None:
        return 1
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
