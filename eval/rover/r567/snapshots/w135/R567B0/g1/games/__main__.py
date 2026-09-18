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
    sys.stdout.write(_MODULES[game_id].solve(sys.stdin.read()))


if __name__ == '__main__':
    main()
