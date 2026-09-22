import sys

from games import life, nim, sub, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> int:
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in MODULES:
        return 2
    text = sys.stdin.read()
    out = MODULES[args[0]].solve(text)
    if out:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
