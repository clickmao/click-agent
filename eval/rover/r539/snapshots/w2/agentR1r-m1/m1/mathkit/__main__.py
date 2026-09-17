"""CLI entry point for mathkit."""

import json
import sys

from . import graphs, linear, modular, prob

_OPS = {
    "qr_count": (modular, "qr_count"),
    "choose": (modular, "choose"),
    "det": (linear, "det"),
    "shortest": (graphs, "shortest"),
    "expect": (prob, "expect"),
}


def main(argv):
    op = argv[1]
    mod, fn_name = _OPS[op]
    args = json.loads(sys.stdin.read())
    out = getattr(mod, fn_name)(args)
    sys.stdout.write(out + "\n")


if __name__ == "__main__":
    main(sys.argv)
