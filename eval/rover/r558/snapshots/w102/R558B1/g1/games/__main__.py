"""CLI 入口：python3 -m games <game_id>"""

import sys

from . import life, sub, nim, wythoff

_TABLE = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main() -> int:
    args = sys.argv[1:]
    fn = _TABLE[args[0]]
    text = sys.stdin.read()
    out = fn(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
