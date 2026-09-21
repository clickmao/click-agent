"""CLI 入口：python3 -m games <game_id>。"""
import sys

from . import life, nim, sub, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return 2
    mod = _MODULES.get(argv[0])
    if mod is None:
        return 2
    text = sys.stdin.read()
    out = mod.solve(text)
    if out:
        sys.stdout.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
