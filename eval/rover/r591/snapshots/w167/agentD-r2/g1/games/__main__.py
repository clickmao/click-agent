import sys

from games import life, sub, nim, wythoff

_GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    gid = sys.argv[1].strip() if len(sys.argv) > 1 else ''
    if gid not in _GAMES:
        return 2
    data = sys.stdin.read()
    out = _GAMES[gid].solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
