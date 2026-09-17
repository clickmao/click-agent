"""CLI entry: ``python3 -m mathkit <op>``.

Reads a JSON object from stdin, dispatches to the op's pure function,
writes the returned string to stdout (exactly one line, no extras).
Silent on stderr.
"""

import json
import sys

from . import modular, linear, graphs, prob

_OPS = {
    "qr_count": modular.qr_count,
    "choose": modular.choose,
    "det": linear.det,
    "shortest": graphs.shortest,
    "expect": prob.expect,
}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return 2
    op = args[0]
    fn = _OPS.get(op)
    if fn is None:
        return 2
    payload = sys.stdin.read()
    try:
        params = json.loads(payload) if payload.strip() else {}
    except ValueError:
        return 2
    out = fn(params)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
