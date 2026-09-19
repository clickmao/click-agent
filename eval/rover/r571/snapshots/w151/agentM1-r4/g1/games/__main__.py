"""CLI 入口：python3 -m games <game_id>，从 stdin 读全文，把 solve 的返回值写到 stdout。"""

import sys


def main():
    game = sys.argv[1]
    if game == 'life':
        from games.life import solve
    elif game == 'sub':
        from games.sub import solve
    elif game == 'nim':
        from games.nim import solve
    elif game == 'wythoff':
        from games.wythoff import solve
    else:
        return
    text = sys.stdin.read()
    out = solve(text)
    sys.stdout.write(out + '\n')


if __name__ == '__main__':
    main()
