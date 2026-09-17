import sys


def main():
    args = sys.argv[1:]
    if len(args) != 1:
        return
    name = args[0]
    data = sys.stdin.read()
    if name == 'vm':
        from .vm import solve
    elif name == 'jsonmini':
        from .jsonmini import solve
    elif name == 'vm_run':
        from .vm import solve
    elif name == 'json_mini':
        from .jsonmini import solve
    else:
        return
    sys.stdout.write(solve(data))


if __name__ == '__main__':
    main()
