"""CLI entry: python3 -m games <game_id>; reads stdin, writes the solver output.

<game_id> in {life, sub, nim, wythoff}.
"""
import sys

from . import life, sub, nim, wythoff

_GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in _GAMES:
        return 2
    text = sys.stdin.read()
    out = _GAMES[args[0]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
