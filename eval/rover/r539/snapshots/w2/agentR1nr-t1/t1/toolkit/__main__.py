import sys

from toolkit import vm, jsonmini

MODULES = {
    'vm': vm,
    'jsonmini': jsonmini,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in MODULES:
        return 1
    text = sys.stdin.read()
    result = MODULES[sys.argv[1]].solve(text)
    sys.stdout.write(result)
    return 0


if __name__ == '__main__':
    sys.exit(main())
