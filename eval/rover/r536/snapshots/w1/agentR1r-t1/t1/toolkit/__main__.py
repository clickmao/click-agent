import sys

from toolkit import jsonmini, vm

_MODS = {"vm": vm, "jsonmini": jsonmini}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in _MODS:
        sys.exit(1)
    text = sys.stdin.read()
    out = _MODS[sys.argv[1]].solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
