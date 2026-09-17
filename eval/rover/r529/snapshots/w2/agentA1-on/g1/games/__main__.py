"""CLI entry: python3 -m games <game_id> with game_id in {life, sub, nim, wythoff}.

Reads all of stdin, calls the module's solve(), writes the result to stdout.
"""
import sys

from . import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in _MODULES:
        return 2
    text = sys.stdin.read()
    out = _MODULES[args[0]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
