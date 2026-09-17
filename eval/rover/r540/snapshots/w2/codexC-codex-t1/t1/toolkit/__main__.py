"""CLI entry point for the multi-file toolkit."""

import sys

from . import jsonmini, vm

_COMMANDS = {
    "vm": vm.solve,
    "jsonmini": jsonmini.solve,
}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        return 1
    handler = _COMMANDS.get(args[0])
    if handler is None:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(handler(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
