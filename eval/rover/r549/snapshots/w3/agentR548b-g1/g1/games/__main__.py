import sys

from games import life, nim, sub, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game_id = sys.argv[1]
    data = sys.stdin.read()
    out = MODULES[game_id].solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
