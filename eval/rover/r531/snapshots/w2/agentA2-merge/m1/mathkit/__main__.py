"""CLI entry point: python3 -m mathkit <op>

Reads a single JSON object from stdin, dispatches to the matching pure
function in the owning module, and writes the returned string to stdout.
Silent on stderr; output is exactly one line.
"""

import json
import sys

from . import graphs, linear, modular, prob

# op name -> callable(args: dict) -> str
OPS = {
    "qr_count": modular.qr_count,
    "choose": modular.choose,
    "det": linear.det,
    "shortest": graphs.shortest,
    "expect": prob.expect,
}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return 2
    op = argv[0]
    fn = OPS.get(op)
    if fn is None:
        return 2
    payload = sys.stdin.read()
    args = json.loads(payload) if payload.strip() else {}
    sys.stdout.write(fn(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
