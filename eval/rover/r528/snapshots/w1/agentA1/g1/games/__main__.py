"""CLI entry: ``python3 -m games <game_id>`` (life|sub|nim|wythoff)."""

import sys


def main(argv):
    if len(argv) != 2:
        return 2
    game_id = argv[1]
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
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
