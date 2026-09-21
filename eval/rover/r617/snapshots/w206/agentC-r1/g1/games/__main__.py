"""CLI entry: python3 -m games <game_id> (life|sub|nim|wythoff)."""

import sys


def main(argv):
    if len(argv) != 2:
        return 1
    game_id = argv[1]
    if game_id not in ("life", "sub", "nim", "wythoff"):
        return 1
    if game_id == "life":
        from . import life as mod
    elif game_id == "sub":
        from . import sub as mod
    elif game_id == "nim":
        from . import nim as mod
    else:
        from . import wythoff as mod
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
