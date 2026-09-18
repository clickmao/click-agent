"""games 包 CLI 入口：python3 -m games <game_id>，从 stdin 读全文、写出 solve 结果。"""
import sys


def main(argv):
    if len(argv) != 1 or argv[0] not in ('life', 'sub', 'nim', 'wythoff'):
        return
    text = sys.stdin.read()
    if argv[0] == 'life':
        from games.life import solve
    elif argv[0] == 'sub':
        from games.sub import solve
    elif argv[0] == 'nim':
        from games.nim import solve
    else:
        from games.wythoff import solve
    sys.stdout.write(solve(text))


if __name__ == '__main__':
    main(sys.argv[1:])
