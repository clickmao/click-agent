"""CLI entry point: python3 -m mathkit <op> with JSON args on stdin."""

import json
import sys

from . import graphs, linear, modular, prob

OPS = {
    "qr_count": modular.qr_count,
    "choose": modular.choose,
    "det": linear.det,
    "shortest": graphs.shortest,
    "expect": prob.expect,
}


def main() -> int:
    op = sys.argv[1]
    args = json.loads(sys.stdin.read())
    sys.stdout.write(OPS[op](args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
