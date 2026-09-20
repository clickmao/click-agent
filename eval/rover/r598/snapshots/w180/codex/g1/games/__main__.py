"""CLI entry point: python3 -m games <game_id> reads stdin, writes stdout."""

import sys

from . import life, nim, sub, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in _MODULES:
        return 2
    text = sys.stdin.read()
    out = _MODULES[argv[0]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
