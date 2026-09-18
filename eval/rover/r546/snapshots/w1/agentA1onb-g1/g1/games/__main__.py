"""CLI entry point: ``python3 -m games <game_id>``.

Reads the whole stdin, dispatches to the game module's ``solve`` and writes the
result verbatim to stdout.  Nothing is printed to stderr.
"""

from __future__ import annotations

import sys

from . import life, nim, sub, wythoff

_GAMES = {
    'life': life.solve,
    'sub': sub.solve,
    'nim': nim.solve,
    'wythoff': wythoff.solve,
}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return 2
    game_id = argv[1]
    solver = _GAMES.get(game_id)
    if solver is None:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(solver(text))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
