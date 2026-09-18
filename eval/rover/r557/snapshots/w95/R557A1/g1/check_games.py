"""Byte-exact check of the four games against the public examples."""

import subprocess
import sys

CASES = [
    (
        "life",
        "11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n",
        ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n.....",
    ),
    (
        "life",
        "11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n",
        "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n..",
    ),
    ("sub", "31 3\n1 6 10\n", "WIN 6"),
    ("sub", "19 1\n1\n", "WIN 1"),
    ("nim", "3\n5 9 4\n", "WIN 2 8"),
    ("nim", "1\n3\n", "WIN 1 3"),
    ("wythoff", "21 25\n", "WIN 15 15"),
    ("wythoff", "10 9\n", "WIN 0 3"),
]


def main() -> int:
    ok = True
    for game, stdin, want in CASES:
        proc = subprocess.run(
            [sys.executable, "-m", "games", game],
            input=stdin,
            capture_output=True,
            text=True,
        )
        got = proc.stdout
        status = "OK" if got == want else "FAIL"
        if got != want:
            ok = False
        if proc.stderr != "":
            ok = False
            status += " (stderr not empty)"
        print("%s %s rc=%d" % (status, game, proc.returncode))
        if got != want:
            print("  want: %r" % want)
            print("  got : %r" % got)
    print("ALL OK" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
