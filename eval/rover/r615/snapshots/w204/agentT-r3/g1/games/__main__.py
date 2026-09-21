import sys


def main() -> None:
    args = sys.argv[1:]
    game_id = args[0] if args else ""
    text = sys.stdin.read()
    if game_id == "life":
        from games.life import solve
    elif game_id == "sub":
        from games.sub import solve
    elif game_id == "nim":
        from games.nim import solve
    elif game_id == "wythoff":
        from games.wythoff import solve
    else:
        return
    sys.stdout.write(solve(text))


if __name__ == "__main__":
    main()
