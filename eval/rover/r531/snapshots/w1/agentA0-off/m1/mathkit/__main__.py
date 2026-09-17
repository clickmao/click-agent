"""CLI entry: ``python3 -m mathkit <op>``.

Reads a single JSON object from stdin, dispatches to the op function, and
writes exactly one line (the answer, no trailing newline) to stdout.  No other
text is ever printed; stderr stays silent.
"""

import json
import sys

from mathkit import graphs, linear, modular, prob

_OPS = {
    "qr_count": modular.qr_count,
    "choose": modular.choose,
    "det": linear.det,
    "shortest": graphs.shortest,
    "expect": prob.expect,
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return 2
    op = argv[0]
    fn = _OPS.get(op)
    if fn is None:
        return 2
    raw = sys.stdin.read()
    try:
        args = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return 2
    out = fn(args)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
