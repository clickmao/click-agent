import sys

from . import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    if len(sys.argv) < 2:
        return 1
    name = sys.argv[1]
    if name not in MODULES:
        return 1
    text = sys.stdin.read()
    out = MODULES[name].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
