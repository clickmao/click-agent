"""CLI entry: python3 -m toolkit <vm|jsonmini>

reads all of stdin (surrogateescape, so lone surrogates from \\uD800-\\uDFFF
round-trip), calls the module's solve(), writes result to stdout as UTF-8
with surrogateescape (never crashes on surrogates, preserves unknown bytes).
no extra output (stderr silent), exit code 0 on success.
"""

import sys


def main(argv) -> int:
    if len(argv) != 2 or argv[1] not in ("vm", "jsonmini"):
        return 2
    data = sys.stdin.buffer.read().decode("utf-8", "surrogateescape")
    if argv[1] == "vm":
        from toolkit import vm as mod
    else:
        from toolkit import jsonmini as mod
    out = mod.solve(data)
    sys.stdout.buffer.write(out.encode("utf-8", "surrogateescape"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
