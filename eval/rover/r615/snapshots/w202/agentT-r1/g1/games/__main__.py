"""CLI 入口: python3 -m games <game_id>, game_id in {life, sub, nim, wythoff}。"""

import sys


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        return 1
    gid = argv[0]
    if gid == "life":
        from .life import solve
    elif gid == "sub":
        from .sub import solve
    elif gid == "nim":
        from .nim import solve
    elif gid == "wythoff":
        from .wythoff import solve
    else:
        return 1

    data = sys.stdin.read()
    out = solve(data)
    sys.stdout.write(out)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
