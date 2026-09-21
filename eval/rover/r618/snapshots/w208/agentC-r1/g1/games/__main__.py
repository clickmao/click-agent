import sys

from . import life, sub, nim, wythoff

MODS = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> int:
    gid = sys.argv[1]
    text = sys.stdin.read()
    out = MODS[gid].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
