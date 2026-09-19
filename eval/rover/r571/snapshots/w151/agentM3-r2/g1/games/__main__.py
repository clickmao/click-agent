"""CLI entry: python3 -m games <game_id>

Reads all of stdin, calls the game module's solve, writes the returned
string to stdout (no trailing newline, no extra output, silent stderr).
"""

import sys

from games import life, sub, nim, wythoff

_GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _GAMES:
        return 1
    text = sys.stdin.read()
    out = _GAMES[argv[0]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
