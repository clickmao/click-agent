"""CLI 入口: python3 -m games <game_id>。"""
import sys


def main():
    if len(sys.argv) < 2:
        return
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
        return
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))


if __name__ == '__main__':
    main()
