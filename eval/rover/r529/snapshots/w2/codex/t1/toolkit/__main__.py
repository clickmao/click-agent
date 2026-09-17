import sys

from . import jsonmini, vm


def main() -> None:
    if len(sys.argv) < 2:
        sys.stdout.write("ERR")
        return
    name = sys.argv[1]
    if name == "vm":
        module = vm
    elif name == "jsonmini":
        module = jsonmini
    else:
        sys.stdout.write("ERR")
        return
    text = sys.stdin.read()
    out = module.solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
