import sys

from toolkit import vm, jsonmini

MODULES = {
    'vm': vm,
    'jsonmini': jsonmini,
}


def main():
    args = sys.argv[1:]
    if len(args) != 1 or args[0].replace('_', '') not in MODULES:
        sys.exit(2)
    mod = MODULES[args[0].replace('_', '')]
    data = sys.stdin.read()
    sys.stdout.write(mod.solve(data))


if __name__ == '__main__':
    main()
