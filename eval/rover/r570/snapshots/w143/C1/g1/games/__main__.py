"""CLI entry point: python3 -m games <game_id>."""

import sys

from . import life, nim, sub, wythoff

_GAMES = {
    "life": life.solve,
    "sub": sub.solve,
    "nim": nim.solve,
    "wythoff": wythoff.solve,
}


def main() -> None:
    game_id = sys.argv[1] if len(sys.argv) > 1 else ""
    if game_id not in _GAMES:
        return
    text = sys.stdin.read()
    sys.stdout.write(_GAMES[game_id](text))


if __name__ == "__main__":
    main()
