"""CLI entry point: ``python3 -m games <game_id>``.

Reads the entire standard input, dispatches to the requested game module's
``solve`` function and writes the returned text to standard output.  No
extra text is written to stdout or stderr.
"""

import sys

from games import life, nim, sub, wythoff

# game_id -> module exposing a pure ``solve(text: str) -> str`` function.
_GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in _GAMES:
        return 2
    text = sys.stdin.read()
    result = _GAMES[argv[0]].solve(text)
    sys.stdout.write(result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
