"""Headless self-test for the games package.

Runs every public case through the real CLI (python3 -m games <id>) and
compares stdout byte-for-byte, plus a few invariant/negative controls.

Usage:  python3 games/_selftest.py      # prints PASS/FAIL, exit 0 / 1
"""

import subprocess
import sys

CASES = [
    ("life",
     "11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n",
     ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."),
    ("life",
     "11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n",
     "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."),
    ("sub", "31 3\n1 6 10\n", "WIN 6"),
    ("sub", "19 1\n1\n", "WIN 1"),
    ("nim", "3\n5 9 4\n", "WIN 2 8"),
    ("nim", "1\n3\n", "WIN 1 3"),
    ("wythoff", "21 25\n", "WIN 15 15"),
    ("wythoff", "10 9\n", "WIN 0 3"),
]


def run(game, text):
    p = subprocess.run(
        [sys.executable, "-m", "games", game],
        input=text, capture_output=True, text=True,
    )
    return p.stdout, p.stderr, p.returncode


def main():
    failures = 0
    for idx, (game, text, expected) in enumerate(CASES):
        out, err, rc = run(game, text)
        ok = (out == expected) and (rc == 0) and (err == "")
        if not ok:
            failures += 1
            print("FAIL case %d (%s): rc=%d" % (idx, game, rc))
            print("  expected=%r" % expected)
            print("  got     =%r" % out)
            if err:
                print("  stderr  =%r" % err)

    # Negative control: cold Wythoff position must print LOSE, not WIN.
    out, _, _ = run("wythoff", "1 2\n")
    if out != "LOSE":
        failures += 1
        print("FAIL negative control wythoff 1 2 -> %r" % out)

    # Invariant: LOSE iff xor==0 for nim.
    for text, want in [("2\n1 1\n", "LOSE"), ("2\n1 2\n", "WIN 2 1")]:
        out, _, _ = run("nim", text)
        if out != want:
            failures += 1
            print("FAIL nim invariant %r -> %r" % (text, out))

    print("PASS" if failures == 0 else "FAIL")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
