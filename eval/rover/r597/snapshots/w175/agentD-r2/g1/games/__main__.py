import sys

from games import life, sub, nim, wythoff

_MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    out = _MODULES[game_id].solve(text)
    sys.stdout.write(out + '\n' if out else '')


if __name__ == '__main__':
    main()
