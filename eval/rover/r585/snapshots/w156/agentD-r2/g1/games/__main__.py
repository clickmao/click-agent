"""CLI entry point: python3 -m games <game_id> with game_id in life/sub/nim/wythoff.

Reads all of stdin, calls games.<game_id>.solve on the decoded text, and writes
the returned string to stdout with no extra characters and a silent stderr.
"""

import sys


GAMES = ("life", "sub", "nim", "wythoff")


def main(argv) -> int:
    if len(argv) != 2:
        return 1
    game_id = argv[1]
    if game_id not in GAMES:
        return 1
    module = __import__("games." + game_id, fromlist=["solve"])
    text = sys.stdin.read()
    out = module.solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
