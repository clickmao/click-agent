"""CLI entry point: python3 -m games <game_id>."""

import sys

MODULES = ("life", "sub", "nim", "wythoff")


def main(argv):
    if len(argv) != 2 or argv[1] not in MODULES:
        return 1
    name = argv[1]
    mod = __import__("games." + name, fromlist=["solve"])
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
