"""CLI entry: python3 -m mathkit <op>, JSON args on stdin, one-line answer on stdout."""

import json
import sys

from .prob import expect
from .graphs import shortest
from .linear import det
from .modular import choose, qr_count

OPS = {
    "qr_count": qr_count,
    "choose": choose,
    "det": det,
    "shortest": shortest,
    "expect": expect,
}


def main() -> int:
    op = sys.argv[1]
    args = json.loads(sys.stdin.read())
    sys.stdout.write(OPS[op](args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
