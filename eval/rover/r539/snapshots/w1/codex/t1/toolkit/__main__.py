import sys

from toolkit import jsonmini, vm

_MODULES = {
    "vm": vm,
    "jsonmini": jsonmini,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _MODULES:
        return 1
    module = _MODULES[argv[0]]
    text = sys.stdin.read()
    sys.stdout.write(module.solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
