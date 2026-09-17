"""CLI entry point: ``python3 -m toolkit <vm|jsonmini>``."""

import sys

from . import jsonmini, vm

_COMMANDS = {
    "vm": vm.solve,
    "jsonmini": jsonmini.solve,
}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in _COMMANDS:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(_COMMANDS[args[0]](text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
