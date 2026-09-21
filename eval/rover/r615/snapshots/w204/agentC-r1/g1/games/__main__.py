"""CLI entry point: python3 -m games <game_id>."""
import sys


def main(argv):
    if len(argv) != 1 or argv[0] not in ("life", "sub", "nim", "wythoff"):
        return 1
    mod = __import__("games." + argv[0], fromlist=["solve"])
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
