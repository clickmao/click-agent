"""CLI entry point: python3 -m games <game_id>."""
import sys

from games import life, sub, nim, wythoff

GAMES = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in GAMES:
        return
    text = sys.stdin.read()
    sys.stdout.write(GAMES[sys.argv[1]].solve(text))


if __name__ == '__main__':
    main()
