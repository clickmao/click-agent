"""CLI 入口: python3 -m games <game_id>, game_id 取 life/sub/nim/wythoff。"""
import sys

from games import life, nim, sub, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    game_id = argv[0] if argv else ''
    mod = MODULES.get(game_id)
    if mod is None:
        sys.exit(2)
    data = sys.stdin.read()
    sys.stdout.write(mod.solve(data))


if __name__ == '__main__':
    main()
