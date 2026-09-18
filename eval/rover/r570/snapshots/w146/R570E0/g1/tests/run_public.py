"""Byte-exact check of the public examples for all four games."""

import subprocess
import sys

CASES = [
    ("life", "11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n",
     ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."),
    ("life", "11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n",
     "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."),
    ("sub", "31 3\n1 6 10\n", "WIN 6"),
    ("sub", "19 1\n1\n", "WIN 1"),
    ("nim", "3\n5 9 4\n", "WIN 2 8"),
    ("nim", "1\n3\n", "WIN 1 3"),
    ("wythoff", "21 25\n", "WIN 15 15"),
    ("wythoff", "10 9\n", "WIN 0 3"),
]


def main() -> int:
    ok = True
    for idx, (game, inp, want) in enumerate(CASES):
        proc = subprocess.run(
            [sys.executable, "-m", "games", game],
            input=inp.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        got = proc.stdout.decode()
        status = "OK" if got == want else "FAIL"
        if got != want:
            ok = False
        print("case %d %s %s" % (idx, game, status))
        if got != want:
            print("  want: %r" % (want,))
            print("  got : %r" % (got,))
        if proc.stderr:
            print("  stderr: %r" % (proc.stderr.decode(),))
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
