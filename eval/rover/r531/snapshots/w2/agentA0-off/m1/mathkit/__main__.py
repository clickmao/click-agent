"""CLI entry: python3 -m mathkit <op>  (JSON args on stdin -> answer on stdout)."""

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


def main(argv):
    if len(argv) < 2:
        # silent failure; no extra text on stdout/stderr
        return 2
    op = argv[1]
    fn = OPS.get(op)
    if fn is None:
        return 2
    raw = sys.stdin.read()
    args = json.loads(raw) if raw.strip() else {}
    sys.stdout.write(fn(args))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
