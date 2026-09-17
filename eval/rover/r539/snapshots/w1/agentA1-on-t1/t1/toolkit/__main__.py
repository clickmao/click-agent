import sys

from . import vm, jsonmini

_MODULES = {"vm": vm, "jsonmini": jsonmini}


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1 or argv[0] not in _MODULES:
        return 2
    data = sys.stdin.read()
    try:
        result = _MODULES[argv[0]].solve(data)
    except Exception:
        result = "ERR"
    sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
