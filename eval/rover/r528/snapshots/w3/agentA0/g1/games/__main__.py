"""CLI entry: python3 -m games <game_id>  (game_id in life/sub/nim/wythoff).

Reads all of stdin, calls the game module's solve(), writes result to stdout.
No extra output; silent on stderr.
"""
import sys

from . import life, sub, nim, wythoff

_GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in _GAMES:
        return 2
    data = sys.stdin.read()
    out = _GAMES[argv[1]].solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
