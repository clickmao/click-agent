"""CLI entry: python3 -m toolkit <vm|jsonmini>

Reads all of stdin, dispatches to the matching module's solve(), writes the
returned text to stdout. No extra output; stderr stays silent.
"""

import sys


def main(argv):
    if len(argv) != 2 or argv[1] not in ("vm", "jsonmini"):
        return 2
    name = argv[1]
    raw = sys.stdin.buffer.read()
    text = raw.decode("utf-8")
    mod = __import__("toolkit." + name, fromlist=["solve"])
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
