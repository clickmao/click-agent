import sys

from . import life, nim, sub, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in MODULES:
        return 2
    mod = MODULES[sys.argv[1]]
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
