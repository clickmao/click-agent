"""CLI entry: python3 -m toolkit <vm|jsonmini>  (reads stdin, writes stdout)."""
import sys

from . import vm, jsonmini


def main(argv):
    if len(argv) < 2:
        return 2
    name = argv[1]
    data = sys.stdin.read()
    if name == "vm":
        sys.stdout.write(vm.solve(data))
    elif name == "jsonmini":
        sys.stdout.write(jsonmini.solve(data))
    else:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
