"""CLI entry: python3 -m games <game_id>; reads all stdin, writes solve() result."""

import sys


def main() -> int:
    if len(sys.argv) < 2:
        return 2
    game = sys.argv[1]
    if game == 'life':
        from games import life as mod
    elif game == 'sub':
        from games import sub as mod
    elif game == 'nim':
        from games import nim as mod
    elif game == 'wythoff':
        from games import wythoff as mod
    else:
        return 2
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
