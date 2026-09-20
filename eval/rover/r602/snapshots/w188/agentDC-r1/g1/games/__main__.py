"""CLI entry point: python3 -m games <game_id>

Reads all of stdin, dispatches to the module's solve(), and writes the
returned text verbatim to stdout (no trailing newline added).
Silent on success; nothing extra on stdout or stderr.
"""

import sys


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        return 0
    game_id = argv[0]
    if game_id == "life":
        from games.life import solve
    elif game_id == "sub":
        from games.sub import solve
    elif game_id == "nim":
        from games.nim import solve
    elif game_id == "wythoff":
        from games.wythoff import solve
    else:
        return 0

    text = sys.stdin.read()
    out = solve(text)
    if out:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
