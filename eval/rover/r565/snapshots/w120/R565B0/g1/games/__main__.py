"""CLI entry: python3 -m games <life|sub|nim|wythoff>"""

import sys


def main():
    argv = sys.argv[1:]
    gid = argv[0] if argv else ""
    text = sys.stdin.read()
    if gid == "life":
        from games.life import solve
    elif gid == "sub":
        from games.sub import solve
    elif gid == "nim":
        from games.nim import solve
    elif gid == "wythoff":
        from games.wythoff import solve
    else:
        return
    out = solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
