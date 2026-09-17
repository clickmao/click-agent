"""CLI entry point: ``python3 -m games <game_id>``.

Reads the whole of stdin, dispatches to the game module's ``solve`` and writes
the returned text to stdout verbatim (nothing extra on stdout or stderr).

Usage:
    python3 -m games life     # Conway's Game of Life
    python3 -m games sub      # subtraction game
    python3 -m games nim      # multi-pile Nim
    python3 -m games wythoff  # Wythoff's game

Run the built-in self-test with:
    python3 -m games --selftest
"""

import sys

_GAMES = {
    "life": "games.life",
    "sub": "games.sub",
    "nim": "games.nim",
    "wythoff": "games.wythoff",
}


def _load(game_id: str):
    import importlib

    return importlib.import_module(_GAMES[game_id])


def _run(game_id: str) -> int:
    module = _load(game_id)
    text = sys.stdin.read()
    out = module.solve(text)
    if out:
        sys.stdout.write(out)
    return 0


def _selftest() -> int:
    """Headless self-check covering the core invariants of all four games."""
    cases = [
        # --- life: spec examples, k=0 identity, boundary/negative controls ---
        ("life",
         "11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n",
         ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."),
        ("life",
         "11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n",
         "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."),
        ("life", "1 1 0\n#\n", "#"),
        ("life", "1 1 1\n#\n", "."),            # negative control: lone cell dies
        ("life", "2 2 1\n.#\n#.\n", "..\n.."),   # negative control: dies out
        # --- sub: examples + boundary + negative controls ---
        ("sub", "31 3\n1 6 10\n", "WIN 6"),
        ("sub", "19 1\n1\n", "WIN 1"),
        ("sub", "1 1\n1\n", "WIN 1"),
        ("sub", "2 1\n2\n", "WIN 2"),            # take 2 at once wins
        ("sub", "2 2\n1 2\n", "WIN 2"),          # minimal winning move is 2
        ("sub", "3 1\n3\n", "WIN 3"),
        # --- nim: examples + boundary + negative controls ---
        ("nim", "3\n5 9 4\n", "WIN 2 8"),
        ("nim", "1\n3\n", "WIN 1 3"),
        ("nim", "2\n1 1\n", "LOSE"),             # negative control: balanced
        ("nim", "4\n1 2 3 4\n", "WIN 4 4"),      # only pile 4 can zero the xor
        ("nim", "3\n3 5 6\n", "LOSE"),           # 3^5^6 == 0
        # --- wythoff: examples + boundary + negative controls ---
        ("wythoff", "21 25\n", "WIN 15 15"),
        ("wythoff", "10 9\n", "WIN 0 3"),
        ("wythoff", "1 1\n", "WIN 1 1"),         # (1,1)->(0,0) diagonal move
        ("wythoff", "1 2\n", "LOSE"),            # first real P-position
        ("wythoff", "3 5\n", "LOSE"),
        ("wythoff", "4 7\n", "LOSE"),
        ("wythoff", "2 2\n", "WIN 0 1"),         # lexicographically smallest
    ]
    fails = 0
    for game_id, stdin, want in cases:
        got = _load(game_id).solve(stdin)
        if got != want:
            fails += 1
            sys.stderr.write("FAIL %s\n  got =%r\n  want=%r\n" % (game_id, got, want))
    sys.stdout.write("PASS %d/%d\n" % (len(cases) - fails, len(cases)))
    return 1 if fails else 0


def main(argv) -> int:
    if len(argv) >= 1 and argv[0] == "--selftest":
        return _selftest()
    if len(argv) != 1 or argv[0] not in _GAMES:
        sys.stderr.write("usage: python3 -m games {life|sub|nim|wythoff}\n")
        return 2
    return _run(argv[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
