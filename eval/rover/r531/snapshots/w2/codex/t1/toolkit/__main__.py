import sys

from . import jsonmini, vm

_MODULES = {"vm": vm, "jsonmini": jsonmini}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in _MODULES:
        return
    data = sys.stdin.read()
    sys.stdout.write(_MODULES[sys.argv[1]].solve(data))


if __name__ == "__main__":
    main()
