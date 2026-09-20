import sys

def main():
    argv = sys.argv[1:]
    if not argv:
        return
    game = argv[0]
    text = sys.stdin.read()
    if game == "life":
        from games.life import solve
    elif game == "sub":
        from games.sub import solve
    elif game == "nim":
        from games.nim import solve
    elif game == "wythoff":
        from games.wythoff import solve
    else:
        return
    out = solve(text)
    sys.stdout.write(out)

if __name__ == "__main__":
    main()
