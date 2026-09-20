"""CLI entry: python3 -m games <game_id> reads all stdin, prints solve() result.

game_id in {life, sub, nim, wythoff}. No extra output on stdout or stderr.
"""
import sys


def main() -> int:
    gid = sys.argv[1]
    if gid == 'life':
        from games import life as mod
    elif gid == 'sub':
        from games import sub as mod
    elif gid == 'nim':
        from games import nim as mod
    elif gid == 'wythoff':
        from games import wythoff as mod
    else:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main())
