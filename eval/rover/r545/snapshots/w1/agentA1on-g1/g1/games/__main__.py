"""CLI entry: python3 -m games <game_id> reads stdin, prints solve() result.

game_id in {life, sub, nim, wythoff}. stdout only; stderr silent.
"""
import sys

from . import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _MODULES:
        return 2
    mod = _MODULES[argv[0]]
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
