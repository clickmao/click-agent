"""Command line entry point: ``python3 -m toolkit <vm|jsonmini>``."""

import sys

from . import jsonmini, vm

_MODULES = {
    "vm": vm,
    "vm_run": vm,
    "jsonmini": jsonmini,
    "json_mini": jsonmini,
}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in _MODULES:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(_MODULES[args[0]].solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
