import sys

from games import life, sub, nim, wythoff

_MODS = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in _MODS:
        return
    text = sys.stdin.read()
    out = _MODS[args[0]].solve(text)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
