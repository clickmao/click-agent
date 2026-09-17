import sys


def main():
    if len(sys.argv) < 2:
        return
    name = sys.argv[1]
    if name == "vm":
        from toolkit import vm as mod
    elif name == "jsonmini":
        from toolkit import jsonmini as mod
    else:
        return
    data = sys.stdin.read()
    result = mod.solve(data)
    sys.stdout.write(result)


if __name__ == "__main__":
    main()
