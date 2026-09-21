import sys

from . import life, nim, sub, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> int:
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in MODULES:
        return 0
    text = sys.stdin.read()
    sys.stdout.write(MODULES[args[0]].solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
