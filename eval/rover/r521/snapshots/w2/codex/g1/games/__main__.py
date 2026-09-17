import sys

from . import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in MODULES:
        return 1
    data = sys.stdin.read()
    out = MODULES[argv[1]].solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
