import sys


def main():
    if len(sys.argv) < 2:
        return
    game = sys.argv[1]
    if game == "life":
        from .life import solve
    elif game == "sub":
        from .sub import solve
    elif game == "nim":
        from .nim import solve
    elif game == "wythoff":
        from .wythoff import solve
    else:
        return
    text = sys.stdin.read()
    out = solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
