import sys


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    text = sys.stdin.read()
    if cmd == 'vm':
        from toolkit import vm as mod
    elif cmd == 'jsonmini':
        from toolkit import jsonmini as mod
    else:
        sys.stdout.write('ERR')
        return
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main()
