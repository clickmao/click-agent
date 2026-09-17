# -*- coding: utf-8 -*-
"""CLI entry: python3 -m toolkit <vm|jsonmini>

Reads all of stdin, calls the module's solve(), writes the result to stdout.
No extra text; stderr stays silent.
"""

import sys

from . import vm as _vm
from . import jsonmini as _jsonmini

_MODULES = {
    "vm": _vm,
    "jsonmini": _jsonmini,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1 or argv[0] not in _MODULES:
        return 2
    data = sys.stdin.read()
    out = _MODULES[argv[0]].solve(data)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
