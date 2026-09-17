"""CLI entry point: ``python3 -m games <game_id>``.

Reads all of stdin, dispatches to the game module's ``solve``, writes the
result to stdout with exactly one trailing newline. Nothing is written to
stderr; a bad game id exits with a non-zero status silently.
"""

import sys

from . import GAME_IDS


def _load(game_id: str):
    if game_id == "life":
        from . import life as mod
    elif game_id == "sub":
        from . import sub as mod
    elif game_id == "nim":
        from . import nim as mod
    elif game_id == "wythoff":
        from . import wythoff as mod
    else:
        return None
    return mod


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in GAME_IDS:
        return 2
    mod = _load(argv[0])
    if mod is None:
        return 2
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
