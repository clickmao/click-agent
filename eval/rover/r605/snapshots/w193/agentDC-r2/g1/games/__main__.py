"""CLI entry point: python3 -m games <game_id> reads stdin, writes solve() output."""
import sys

from games import life, sub, nim, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv):
    if len(argv) < 2:
        return 1
    game_id = argv[1]
    mod = _MODULES.get(game_id)
    if mod is None:
        return 1
    text = sys.stdin.read()
    sys.stdout.write(mod.solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
