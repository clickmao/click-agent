"""CLI entry: python3 -m toolkit <vm|jsonmini>

Reads all of stdin, dispatches to the subcommand's solve(), writes result
to stdout with no trailing newline. Silent on stderr. Exit 0 on success,
non-zero on usage error.
"""

import sys


def main(argv):
    if len(argv) != 2 or argv[1] not in ("vm", "jsonmini"):
        return 2
    if argv[1] == "vm":
        from . import vm as mod
    else:
        from . import jsonmini as mod
    data = sys.stdin.buffer.read().decode("utf-8")
    result = mod.solve(data)
    sys.stdout.buffer.write(result.encode("utf-8"))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
