"""CLI 入口：python3 -m games <game_id>，读 stdin 全部文本，写 solve 的返回值。"""
import sys

from . import life, sub, nim, wythoff

_GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main(argv):
    text = sys.stdin.read()
    out = _GAMES[argv[0]](text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
