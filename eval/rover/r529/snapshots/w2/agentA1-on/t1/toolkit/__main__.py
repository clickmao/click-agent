import sys

from . import vm, jsonmini

_MODULES = {"vm": vm, "jsonmini": jsonmini}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in _MODULES:
        return 1
    data = sys.stdin.read()
    out = _MODULES[args[0]].solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
