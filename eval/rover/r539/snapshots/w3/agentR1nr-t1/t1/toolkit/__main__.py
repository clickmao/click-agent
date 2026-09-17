import sys


def main():
    argv = sys.argv[1:]
    if len(argv) != 1:
        return
    name = argv[0]
    if name == 'vm':
        from toolkit import vm as mod
    elif name == 'jsonmini':
        from toolkit import jsonmini as mod
    else:
        return
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main()
