import sys

from . import life, nim, sub, wythoff

_MODS = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(_MODS[game_id].solve(text))


if __name__ == '__main__':
    main()
