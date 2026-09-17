"""CLI entry point: python3 -m mathkit <op> with JSON args on stdin."""
import json
import sys

from .graphs import shortest
from .linear import det
from .modular import choose, qr_count
from .prob import expect

OPERATIONS = {
    "qr_count": qr_count,
    "choose": choose,
    "det": det,
    "shortest": shortest,
    "expect": expect,
}


def main() -> None:
    args = json.loads(sys.stdin.read())
    sys.stdout.write(OPERATIONS[sys.argv[1]](args))


if __name__ == "__main__":
    main()
