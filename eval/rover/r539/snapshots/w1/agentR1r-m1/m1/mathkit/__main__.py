"""CLI entry point: python3 -m mathkit <op> reads JSON args from stdin."""

import json
import sys

from mathkit import graphs, linear, modular, prob

OPS = {
    "qr_count": modular.qr_count,
    "choose": modular.choose,
    "det": linear.det,
    "shortest": graphs.shortest,
    "expect": prob.expect,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in OPS:
        return 1
    raw = sys.stdin.read()
    args = json.loads(raw)
    sys.stdout.write(OPS[argv[1]](args))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
