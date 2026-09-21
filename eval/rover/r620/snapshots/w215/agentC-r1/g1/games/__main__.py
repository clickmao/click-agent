"""CLI: python3 -m games <game_id>，读 stdin，写 stdout。"""
import sys

from . import life, nim, sub, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game = sys.argv[1]
    mod = MODULES[game]
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
