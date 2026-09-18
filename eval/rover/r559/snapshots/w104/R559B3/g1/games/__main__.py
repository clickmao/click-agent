import sys

from games import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game_id = sys.argv[1]
    mod = MODULES[game_id]
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
