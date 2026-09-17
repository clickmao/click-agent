"""CLI entry: python3 -m games <game_id>  (life/sub/nim/wythoff)."""
import sys

from . import life, sub, nim, wythoff

_MODULES = {"life": life, "sub": sub, "nim": nim, "wythoff": wythoff}


def main() -> int:
    if len(sys.argv) < 2:
        return 2
    mod = _MODULES.get(sys.argv[1])
    if mod is None:
        return 2
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
