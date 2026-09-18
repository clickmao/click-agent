"""CLI entry point: python3 -m games <game_id>"""
import sys

from games import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    args = sys.argv[1:]
    game = args[0]
    text = sys.stdin.read()
    out = MODULES[game].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
