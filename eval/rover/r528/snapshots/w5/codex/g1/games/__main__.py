import sys

from . import life, nim, sub, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) < 2 or argv[1] not in _MODULES:
        return
    text = sys.stdin.read()
    sys.stdout.write(_MODULES[argv[1]].solve(text))


if __name__ == "__main__":
    main(sys.argv)
