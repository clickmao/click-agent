"""CLI entry point: ``python3 -m games <game_id>`` reads stdin, writes stdout."""

import sys

from games import life, sub, nim, wythoff

MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in MODULES:
        return 2
    game_id = sys.argv[1]
    text = sys.stdin.read()
    sys.stdout.write(MODULES[game_id].solve(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
