import sys

from . import vm, jsonmini


def main(argv):
    if len(argv) != 2:
        return 2
    name = argv[1]
    if name == "vm":
        mod = vm
    elif name == "jsonmini":
        mod = jsonmini
    else:
        return 2
    data = sys.stdin.buffer.read().decode("utf-8")
    out = mod.solve(data)
    sys.stdout.buffer.write(out.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
