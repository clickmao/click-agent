"""CLI entry point: python3 -m games <game_id> reads stdin, writes stdout."""

import sys

from . import life, sub, nim, wythoff

_GAMES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> None:
    if len(sys.argv) < 2:
        return
    game = _GAMES.get(sys.argv[1])
    if game is None:
        return
    text = sys.stdin.read()
    out = game.solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
