"""CLI entry: python3 -m toolkit <vm|jsonmini>

Reads all of stdin, dispatches to the subcommand's solve(), writes the result
to stdout. No extra output on stdout or stderr.
"""
import sys


def main(argv):
    if len(argv) != 2:
        return 1
    name = argv[1]
    if name == "vm":
        from toolkit import vm as mod
    elif name == "jsonmini":
        from toolkit import jsonmini as mod
    else:
        return 1
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
