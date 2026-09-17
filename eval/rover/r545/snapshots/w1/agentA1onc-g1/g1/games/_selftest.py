"""Self-test for the games package.  Run: python3 -m games._selftest"""
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


def _run(game, data):
    p = subprocess.run([sys.executable, "-m", "games", game],
                       input=data, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def _finite_check(game, data, expect):
    """Exhaustive/brute-force cross-check for sub, nim, wythoff."""
    if game == "sub":
        toks = data.split()
        n, k = int(toks[0]), int(toks[1])
        moves = sorted(int(t) for t in toks[2:2 + k])
        win = [False] * (n + 1)
        for i in range(1, n + 1):
            win[i] = any(s <= i and not win[i - s] for s in moves)
        if not win[n]:
            return expect == "LOSE"
        m = next(s for s in moves if s <= n and not win[n - s])
        return expect == "WIN %d" % m
    if game == "nim":
        toks = data.split()
        m = int(toks[0])
        piles = [int(t) for t in toks[1:1 + m]]
        x = 0
        for a in piles:
            x ^= a
        if x == 0:
            return expect == "LOSE"
        for idx, a in enumerate(piles, 1):
            if (a ^ x) < a:
                return expect == "WIN %d %d" % (idx, a - (a ^ x))
        return False
    if game == "wythoff":
        a, b = (int(v) for v in data.split())
        # brute force DP over reachable losing set
        lose = set()
        for i in range(a + 1):
            for j in range(b + 1):
                moves = [(i - t, j) for t in range(1, i + 1)] + \
                        [(i, j - t) for t in range(1, j + 1)] + \
                        [(i - t, j - t) for t in range(1, min(i, j) + 1)]
                if not any((p, q) in lose for (p, q) in moves):
                    lose.add((i, j))
        if (a, b) in lose:
            return expect == "LOSE"
        best = None
        for i in range(a + 1):
            for j in range(b + 1):
                if i == 0 and j == 0:
                    continue
                if (i > 0 and j > 0 and i != j):
                    continue  # only single-pile (one coord 0) or equal-move
                if (a - i, b - j) in lose:
                    best = (i, j)
                    break
            if best:
                break
        return best is not None and expect == "WIN %d %d" % best
    return True


def main():
    fails = 0
    for game, data, expect in CASES:
        rc, out, err = _run(game, data)
        ok = (rc == 0 and out == expect and err == "")
        ok = ok and _finite_check(game, data, expect)
        if not ok:
            fails += 1
            print("FAIL %s rc=%s out=%r err=%r" % (game, rc, out, err))
    # negative control: the 'life' blinker-free grid must NOT stay identical
    rc, out, err = _run("life", "3 3 1\n...\n###\n...\n")
    if out != ".#.\n.#.\n.#.":
        fails += 1
        print("FAIL life negative control out=%r" % out)
    # no_formal: self-test is a pure pass/fail harness without integer-arithmetic
    # invariants of the problem itself; checked via exhaustive DP cross-check.
    if fails == 0:
        print("PASS")
        return 0
    print("FAIL %d" % fails)
    return 1


if __name__ == "__main__":
    sys.exit(main())
