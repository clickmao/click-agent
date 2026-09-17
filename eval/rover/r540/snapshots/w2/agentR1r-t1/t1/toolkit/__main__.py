import sys

from . import jsonmini, vm

_MODS = {'vm': vm, 'jsonmini': jsonmini}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in _MODS:
        sys.exit(1)
    mod = _MODS[sys.argv[1]]
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
