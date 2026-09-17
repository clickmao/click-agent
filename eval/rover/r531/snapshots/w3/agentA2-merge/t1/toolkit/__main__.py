import sys

from . import vm, jsonmini

_MODULES = {"vm": vm, "jsonmini": jsonmini}


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1 or argv[0] not in _MODULES:
        return 2
    text = sys.stdin.read()
    out = _MODULES[argv[0]].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
