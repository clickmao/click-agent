"""CLI entry point: `python3 -m toolkit <vm|jsonmini>`."""

import sys

from . import jsonmini, vm

_MODULES = {"vm": vm, "jsonmini": jsonmini}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in _MODULES:
        return 1
    data = sys.stdin.read()
    sys.stdout.write(_MODULES[sys.argv[1]].solve(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
