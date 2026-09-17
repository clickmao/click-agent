"""CLI: python3 -m toolkit <vm|jsonmini>"""
import sys


def main():
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in ("vm", "jsonmini"):
        return
    data = sys.stdin.read()
    if args[0] == "vm":
        from .vm import solve
    else:
        from .jsonmini import solve
    sys.stdout.write(solve(data))


if __name__ == "__main__":
    main()
