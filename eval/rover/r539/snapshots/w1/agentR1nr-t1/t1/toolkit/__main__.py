import sys

import toolkit.vm as vm
import toolkit.jsonmini as jsonmini

MODULES = {'vm': vm, 'jsonmini': jsonmini}


def main():
    argv = sys.argv[1:]
    if len(argv) != 1 or argv[0] not in MODULES:
        sys.exit(1)
    data = sys.stdin.read()
    out = MODULES[argv[0]].solve(data)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
