import sys

from . import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main():
    argv = sys.argv[1:]
    if len(argv) != 1 or argv[0] not in MODULES:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(MODULES[argv[0]].solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
