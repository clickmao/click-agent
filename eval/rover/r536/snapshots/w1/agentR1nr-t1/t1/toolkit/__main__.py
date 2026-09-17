import sys

from . import vm, jsonmini


def main():
    args = sys.argv[1:]
    if len(args) != 1:
        sys.exit(2)
    name = args[0]
    if name == "vm":
        mod = vm
    elif name == "jsonmini":
        mod = jsonmini
    else:
        sys.exit(2)
    data = sys.stdin.read()
    out = mod.solve(data)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
