import sys

from toolkit import jsonmini, vm

SOLVERS = {"vm": vm, "jsonmini": jsonmini}


def main():
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in SOLVERS:
        sys.exit(1)
    text = sys.stdin.read()
    sys.stdout.write(SOLVERS[args[0]].solve(text))


if __name__ == "__main__":
    main()
