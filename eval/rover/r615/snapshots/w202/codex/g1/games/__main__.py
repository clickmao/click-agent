import sys

from . import life, sub, nim, wythoff

MODULES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main(argv):
    if len(argv) < 2 or argv[1] not in MODULES:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(MODULES[argv[1]](text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
