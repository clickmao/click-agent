import sys


def main():
    if len(sys.argv) != 2:
        return
    cmd = sys.argv[1]
    text = sys.stdin.read()
    if cmd == 'vm':
        from toolkit import vm as mod
    elif cmd == 'jsonmini':
        from toolkit import jsonmini as mod
    else:
        return
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main()
