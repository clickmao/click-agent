"""CLI entry point: python3 -m games <game_id>"""

import sys


def main():
    argv = sys.argv[1:]
    if not argv:
        return 2
    game_id = argv[0]
    if game_id == "life":
        import games.life as mod
    elif game_id == "sub":
        import games.sub as mod
    elif game_id == "nim":
        import games.nim as mod
    elif game_id == "wythoff":
        import games.wythoff as mod
    else:
        return 2
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
