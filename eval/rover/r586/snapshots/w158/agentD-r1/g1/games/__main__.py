"""CLI entry: python3 -m games <game_id>

Reads all of stdin, dispatches to the game module's solve(), writes result to stdout.
"""

import sys

from games import life, sub, nim, wythoff

_GAMES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> int:
    game_id = sys.argv[1]
    data = sys.stdin.read()
    sys.stdout.write(_GAMES[game_id].solve(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
