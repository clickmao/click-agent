"""CLI entry point: ``python3 -m mathkit <op>``.

Reads one JSON object from stdin as the argument mapping, dispatches to the
owning module's function, and writes the returned text to stdout followed by
a single newline. Nothing else is ever printed (stdout and stderr stay clean).
"""

import json
import sys

from .graphs import shortest
from .linear import det
from .modular import choose, qr_count
from .prob import expect

# op name -> implementation
OPS = {
    "qr_count": qr_count,
    "choose": choose,
    "det": det,
    "shortest": shortest,
    "expect": expect,
}


def main(argv) -> int:
    if len(argv) != 2:
        return 2
    op = argv[1]
    fn = OPS.get(op)
    if fn is None:
        return 2
    raw = sys.stdin.read()
    args = json.loads(raw) if raw.strip() else {}
    out = fn(args)
    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
