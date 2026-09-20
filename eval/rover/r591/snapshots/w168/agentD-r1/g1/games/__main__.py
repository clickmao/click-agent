"""CLI entry: python3 -m games <game_id> with stdin -> stdout."""

import sys

from games import life, nim, sub, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> None:
    game_id = sys.argv[1]
    mod = _MODULES[game_id]
    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
