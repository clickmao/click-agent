import sys


def main() -> int:
    game_id = sys.argv[1] if len(sys.argv) > 1 else ""
    text = sys.stdin.read()
    if game_id == "life":
        from .life import solve
    elif game_id == "sub":
        from .sub import solve
    elif game_id == "nim":
        from .nim import solve
    elif game_id == "wythoff":
        from .wythoff import solve
    else:
        return 0
    sys.stdout.write(solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
