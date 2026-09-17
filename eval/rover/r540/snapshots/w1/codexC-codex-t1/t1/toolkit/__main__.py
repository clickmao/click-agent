"""python3 -m toolkit <vm|jsonmini> 入口。"""

import sys

from . import jsonmini, vm

_MODULES = {
    "vm": vm,
    "jsonmini": jsonmini,
}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or args[0] not in _MODULES:
        sys.stdout.write("ERR")
        return 0
    data = sys.stdin.read()
    try:
        out = _MODULES[args[0]].solve(data)
    except Exception:
        out = "ERR"
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
