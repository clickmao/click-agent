"""CLI: python3 -m games <game_id>

Reads all of stdin, calls the chosen game's solve(), writes the result to
stdout without an added trailing newline. Silent on stderr.
"""
import sys

from games import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) < 2 or argv[1] not in _MODULES:
        return 1
    text = sys.stdin.read()
    out = _MODULES[argv[1]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
