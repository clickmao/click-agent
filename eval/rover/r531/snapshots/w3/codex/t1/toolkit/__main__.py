import sys

from . import jsonmini, vm

_MODULES = {
    "vm": vm,
    "jsonmini": jsonmini,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _MODULES:
        return 2
    text = sys.stdin.read()
    out = _MODULES[argv[0]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
