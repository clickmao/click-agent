import sys

from . import vm, jsonmini

MODULES = {
    'vm': vm,
    'jsonmini': jsonmini,
}


def main() -> int:
    if len(sys.argv) != 2:
        return 1
    name = sys.argv[1]
    if name not in MODULES:
        return 1
    text = sys.stdin.read()
    result = MODULES[name].solve(text)
    sys.stdout.write(result)
    return 0


if __name__ == '__main__':
    sys.exit(main())
