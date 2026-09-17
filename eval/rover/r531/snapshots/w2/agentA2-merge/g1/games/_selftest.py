"""Self-test for the games package: public + control cases via the CLI entry."""
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

# Control cases with theory-derived expectations, independent of this code.
NEG = [
    ("sub", "4 1\n1\n", "LOSE"),        # moves {1}: even piles are losing
    ("sub", "2 2\n1 3\n", "LOSE"),      # 2 is a P-position (=1+1); 3 -> 1 (W)
    ("nim", "2\n3 3\n", "LOSE"),        # equal piles => XOR 0
    ("wythoff", "1 2\n", "LOSE"),       # cold position
    ("wythoff", "2 1\n", "LOSE"),       # cold, swapped order
    ("life", "1 1 5\n#\n", "."),        # isolated single cell dies
]


def run(game, inp):
    """Invoke the CLI in package form, falling back to the file form."""
    argc = [sys.executable, "-m", "games", game]
    p = subprocess.run(argc, input=inp, capture_output=True, text=True, cwd=ROOT)
    if p.returncode != 0 and p.stderr:
        alt = [sys.executable, os.path.join(ROOT, "games", "__main__.py"), game]
        p2 = subprocess.run(alt, input=inp, capture_output=True, text=True, cwd=ROOT)
        if p2.returncode == 0:
            return p2.returncode, p2.stdout, p2.stderr
    return p.returncode, p.stdout, p.stderr


def check(cases, label, fails):
    for game, inp, exp in cases:
        rc, out, err = run(game, inp)
        if not (rc == 0 and out == exp and err == ""):
            fails.append("%s %s rc=%d got=%r exp=%r err=%r"
                         % (label, game, rc, out, exp, err))
    return fails


def main():
    fails = []
    check(CASES, "case", fails)
    check(NEG, "neg", fails)
    if fails:
        for f in fails:
            print("FAIL " + f)
        print("FAIL %d" % len(fails))
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
