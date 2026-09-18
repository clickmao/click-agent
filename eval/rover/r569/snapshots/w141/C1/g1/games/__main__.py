import sys
from . import life, sub, nim, wythoff

MODULES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in MODULES:
        return
    game_id = sys.argv[1]
    text = sys.stdin.read()
    out = MODULES[game_id].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
