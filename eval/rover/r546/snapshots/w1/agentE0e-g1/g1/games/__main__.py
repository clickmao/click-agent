"""CLI 入口：python3 -m games <game_id>。"""
import sys

from games import life, nim, sub, wythoff

_GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main() -> int:
    game_id = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[game_id].solve(text))
    return 0


if __name__ == '__main__':
    sys.exit(main())
