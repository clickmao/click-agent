"""Self-test for games package. Run: python3 -m games._selftest"""
import itertools
import subprocess
import sys

CASES = [
    ("life", "11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#",
     ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."),
    ("life", "11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#",
     "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."),
    ("sub", "31 3\n1 6 10", "WIN 6"),
    ("sub", "19 1\n1", "WIN 1"),
    ("sub", "4 2\n1 3", "LOSE"),
    ("sub", "5 2\n1 3", "WIN 1"),
    ("nim", "3\n5 9 4", "WIN 2 8"),
    ("nim", "1\n3", "WIN 1 3"),
    ("nim", "2\n3 5", "WIN 2 2"),
    ("wythoff", "21 25", "WIN 15 15"),
    ("wythoff", "10 9", "WIN 0 3"),
    ("wythoff", "3 5", "LOSE"),
    ("wythoff", "1 2", "LOSE"),
    ("wythoff", "1 1", "WIN 1 1"),
]


def check_cli():
    ok = 0
    for gid, inp, exp in CASES:
        p = subprocess.run([sys.executable, "-m", "games", gid],
                           input=inp, capture_output=True, text=True)
        if p.stdout == exp and p.stderr == "":
            ok += 1
        else:
            print("FAIL cli", gid, repr(inp), "->", repr(p.stdout), repr(p.stderr))
    print("cli cases:", ok, "/", len(CASES))
    return ok == len(CASES)


def check_wythoff():
    from functools import lru_cache

    @lru_cache(None)
    def win(x, y):
        if x == 0 and y == 0:
            return False
        if any(not win(x - i, y) for i in range(1, x + 1)):
            return True
        if any(not win(x, y - j) for j in range(1, y + 1)):
            return True
        if any(not win(x - d, y - d) for d in range(1, min(x, y) + 1)):
            return True
        return False

    import games.wythoff as wy
    bad = 0
    for a in range(1, 26):
        for b in range(1, 26):
            cold = not win(a, b)
            if cold != wy._lose(a, b):
                bad += 1
                print("MISMATCH cold", a, b)
            out = wy.solve("%d %d" % (a, b))
            if out != "LOSE":
                _, i, j = out.split()
                if not (not win(a - int(i), b - int(j))):
                    bad += 1
                    print("BAD MOVE", a, b, out)
    print("wythoff mismatches:", bad)
    return bad == 0


def check_nim():
    import games.nim as nm
    bad = 0
    for m in range(1, 5):
        for piles in itertools.product(range(1, 16), repeat=m):
            x = 0
            for a in piles:
                x ^= a
            out = nm.solve("%d\n%s" % (m, " ".join(map(str, piles))))
            if x == 0:
                if out != "LOSE":
                    bad += 1
                    print("NIM expect LOSE", piles, out)
            else:
                p, r = map(int, out.split()[1:])
                after = list(piles)
                after[p - 1] -= r
                y = 0
                for a in after:
                    y ^= a
                if not (0 < r <= piles[p - 1] and y == 0):
                    bad += 1
                    print("NIM bad move", piles, out)
    print("nim mismatches:", bad)
    return bad == 0


def check_sub():
    import games.sub as sb
    bad = 0
    move_sets = [[1], [1, 6, 10], [1, 2], [1, 3], [1, 12], [1, 2, 3]]
    for n in range(1, 81):
        for mv in move_sets:
            out = sb.solve("%d %d\n%s" % (n, len(mv), " ".join(map(str, mv))))
            w = [False] * (n + 1)
            for i in range(1, n + 1):
                w[i] = any(x <= i and not w[i - x] for x in mv)
            if not w[n]:
                if out != "LOSE":
                    bad += 1
                    print("SUB exp LOSE", n, mv, out)
            else:
                got = int(out.split()[1])
                smallest = min(x for x in mv if x <= n and not w[n - x])
                if got != smallest:
                    bad += 1
                    print("SUB not smallest", n, mv, out)
    print("sub mismatches:", bad)
    return bad == 0


def main() -> int:
    results = [check_cli(), check_wythoff(), check_nim(), check_sub()]
    passed = all(results)
    print("SELFTEST", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
