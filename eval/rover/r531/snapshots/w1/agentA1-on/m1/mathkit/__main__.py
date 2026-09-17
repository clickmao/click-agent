"""CLI entry point: ``python3 -m mathkit <op>``.

Reads one JSON object from stdin as the argument dict, dispatches to the
owning module's function, and writes the returned string to stdout.
Silent on stderr; no extra text is printed.
"""

import json
import sys

from . import graphs, linear, modular, prob

_OPS = {
    "qr_count": modular.qr_count,
    "choose": modular.choose,
    "det": linear.det,
    "shortest": graphs.shortest,
    "expect": prob.expect,
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in _OPS:
        return 2
    raw = sys.stdin.read()
    args = json.loads(raw) if raw.strip() else {}
    sys.stdout.write(_OPS[argv[0]](args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
