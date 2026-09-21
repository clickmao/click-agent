import sys

from games import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    mod = _MODULES.get(sys.argv[1])
    if mod is None:
        return 1
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
