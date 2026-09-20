"""CLI 入口: python3 -m games <game_id>; 从 stdin 读全部文本, 输出 solve 的返回值。"""
import sys


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    game_id = sys.argv[1]
    if game_id == 'life':
        from games.life import solve
    elif game_id == 'sub':
        from games.sub import solve
    elif game_id == 'nim':
        from games.nim import solve
    elif game_id == 'wythoff':
        from games.wythoff import solve
    else:
        return 1
    text = sys.stdin.read()
    out = solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
