"""CLI entry point: python3 -m games <game_id>

Reads all of stdin, dispatches to the game module's solve(), writes the returned
text to stdout. No extra output; stderr stays silent.

Usage:
    python3 -m games life
    python3 -m games sub
    python3 -m games nim
    python3 -m games wythoff
"""

import sys


def main(argv):
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
    out = mod.solve(text)
    if out is None:
        out = ""
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
