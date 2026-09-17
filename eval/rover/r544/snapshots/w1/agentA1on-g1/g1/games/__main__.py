"""CLI entry point: ``python3 -m games <game_id>``.

Reads the entire stdin text, dispatches to the selected game's ``solve`` and
writes the returned text to stdout.  No extra output on stdout or stderr.
"""

from __future__ import annotations

import sys

from . import life, nim, sub, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main(argv: list[str]) -> int:
    """Run the requested game on stdin; return a process exit code."""
    if len(argv) != 2 or argv[1] not in _GAMES:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[argv[1]](text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
