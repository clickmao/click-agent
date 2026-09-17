"""CLI entry: python3 -m toolkit <vm|jsonmini>

Reads all of stdin, calls the module's solve(), writes the result to stdout.
Nothing else is written to stdout or stderr.
"""
import sys

from . import vm as _vm
from . import jsonmini as _jsonmini

_MODULES = {
    "vm": _vm,
    "vm_run": _vm,
    "jsonmini": _jsonmini,
    "json_mini": _jsonmini,
}


def main(argv):
    if len(argv) != 2:
        return 1
    mod = _MODULES.get(argv[1])
    if mod is None:
        return 1
    data = sys.stdin.read()
    result = mod.solve(data)
    sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
