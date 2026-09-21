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
        sys.exit(1)
    text = sys.stdin.read()
    result = MODULES[argv[0]].solve(text)
    sys.stdout.write(result)


if __name__ == "__main__":
    main()
