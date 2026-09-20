"""CLI entry: python3 -m games <game_id>."""
import sys

from games import life, nim, sub, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) < 2:
        return 2
    game = argv[1]
    if game not in MODULES:
        return 2
    text = sys.stdin.read()
    out = MODULES[game].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
