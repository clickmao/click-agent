"""CLI entry point: python3 -m games <game_id>"""

import sys

from . import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv=None):
    argv = sys.argv if argv is None else argv
    game_id = argv[1] if len(argv) > 1 else ""
    if game_id not in MODULES:
        return 2
    text = sys.stdin.read()
    out = MODULES[game_id].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
