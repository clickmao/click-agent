import sys

from . import life, sub, nim, wythoff

_MODS = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    game_id = sys.argv[1]
    text = sys.stdin.read()
    out = _MODS[game_id].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
