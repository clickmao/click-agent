"""CLI entry: python3 -m toolkit <vm|jsonmini>

Reads all of stdin, dispatches to the subcommand module's solve(), writes the
result to stdout (no trailing newline added, no extra output, stderr silent).
"""
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
    result = _MODULES[argv[0]].solve(text)
    sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
