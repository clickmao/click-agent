"""Command line entry point for the toolkit package."""

import sys


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1 or argv[0] not in ("vm", "jsonmini"):
        return 2
    name = argv[0]
    if name == "vm":
        from . import vm as mod
    else:
        from . import jsonmini as mod
    data = sys.stdin.read()
    sys.stdout.write(mod.solve(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
