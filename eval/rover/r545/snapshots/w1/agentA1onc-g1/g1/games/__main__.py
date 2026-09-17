"""CLI entry point: ``python3 -m games <game_id>``.

Reads the whole of stdin, dispatches to the matching game module's ``solve``,
and writes the returned text to stdout.  Nothing else is printed; stderr stays
silent on success.  A usage error exits with a non-zero status without emitting
extra text.

Supported <game_id>: life, sub, nim, wythoff
"""

import sys


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        return 2
    game_id = argv[0]

    if game_id == "life":
        from . import life as mod
    elif game_id == "sub":
        from . import sub as mod
    elif game_id == "nim":
        from . import nim as mod
    elif game_id == "wythoff":
        from . import wythoff as mod
    else:
        return 2

    text = sys.stdin.read()
    try:
        out = mod.solve(text)
    except Exception:
        return 1
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
