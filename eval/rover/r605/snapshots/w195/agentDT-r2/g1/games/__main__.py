"""CLI entry: python3 -m games <game_id>

Reads all of stdin, calls the matching module's solve(), writes the
returned text to stdout. No extra output; stderr stays silent.
"""

import sys


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return 2
    game_id = argv[0]
    if game_id == 'life':
        from . import life as mod
    elif game_id == 'sub':
        from . import sub as mod
    elif game_id == 'nim':
        from . import nim as mod
    elif game_id == 'wythoff':
        from . import wythoff as mod
    else:
        return 2
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
