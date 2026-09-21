"""CLI entry: python3 -m games <game_id> reads stdin, writes solve() output."""

import sys

from games import life, sub, nim, wythoff

_GAMES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) != 1 or argv[0] not in _GAMES:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[argv[0]].solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
