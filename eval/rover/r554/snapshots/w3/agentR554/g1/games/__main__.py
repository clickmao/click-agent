import sys

mods = {}

def main():
    if len(sys.argv) < 2:
        return
    gid = sys.argv[1]
    data = sys.stdin.read()
    if gid == 'life':
        from . import life as mod
    elif gid == 'sub':
        from . import sub as mod
    elif gid == 'nim':
        from . import nim as mod
    elif gid == 'wythoff':
        from . import wythoff as mod
    else:
        return
    sys.stdout.write(mod.solve(data))


if __name__ == '__main__':
    main()
