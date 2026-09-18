import sys


def main():
    data = sys.stdin.read()
    args = sys.argv[1:]
    if not args:
        return
    gid = args[0]
    if gid == "life":
        from games import life as mod
    elif gid == "sub":
        from games import sub as mod
    elif gid == "nim":
        from games import nim as mod
    elif gid == "wythoff":
        from games import wythoff as mod
    else:
        return
    out = mod.solve(data)
    if out:
        sys.stdout.write(out + "\n")


if __name__ == "__main__":
    main()
