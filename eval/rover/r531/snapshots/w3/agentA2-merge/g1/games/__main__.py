"""CLI 入口：python3 -m games <game_id>，从 stdin 读全文，写结果到 stdout。"""

import sys

from . import life, sub, nim, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in _GAMES:
        return 2
    data = sys.stdin.read()
    out = _GAMES[argv[0]](data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
