"""CLI 入口: python3 -m games <game_id> ; 从 stdin 读全部文本, 写 solve 结果到 stdout。"""
import sys

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    if len(argv) < 2 or argv[1] not in _MODULES:
        return 1
    data = sys.stdin.read()
    out = _MODULES[argv[1]].solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
