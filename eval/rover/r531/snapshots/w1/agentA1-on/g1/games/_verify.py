"""Independent brute-force verification of every game.

Run: python3 -m games._verify   -> prints PASS/FAIL, exit 0 on pass.
"""

import itertools
import subprocess
import sys

from games._refs import ref_life, ref_sub, ref_nim, ref_wythoff


def call(game, stdin_text):
    p = subprocess.run([sys.executable, "-m", "games", game],
                       input=stdin_text.encode(), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    return p.returncode, p.stdout.decode(), p.stderr.decode()


def main():
    ok = True
    checked = 0

    # life: exhaustive small grids (h,w in 1..3) over k in 0..3.
    n0 = checked
    for h, w in itertools.product(range(1, 4), range(1, 4)):
        for bits in itertools.product(".#", repeat=h * w):
            rows = ["".join(bits[r * w:(r + 1) * w]) for r in range(h)]
            for k in range(0, 4):
                txt = "%d %d %d\n%s\n" % (h, w, k, "\n".join(rows))
                exp = ref_life(txt)
                rc, out, err = call("life", txt)
                checked += 1
                if rc != 0 or out != exp or err:
                    ok = False
                    print("FAIL life", txt, repr(out), repr(exp), repr(err))
    print("life exhaustive checked=%d %s" % (checked - n0, "OK" if ok else "BAD"))

    # sub: exhaustive n<=40 with all move sets from 1..6 containing 1.
    bad = 0
    for k in range(1, 4):
        for moves in itertools.combinations(range(1, 7), k):
            if 1 not in moves:
                continue
            for n in range(1, 41):
                txt = "%d %d\n%s\n" % (n, len(moves), " ".join(map(str, moves)))
                exp = ref_sub(n, list(moves))
                rc, out, err = call("sub", txt)
                checked += 1
                if rc != 0 or out != exp or err:
                    bad += 1
                    ok = False
                    if bad <= 5:
                        print("FAIL sub", txt, repr(out), repr(exp))
    print("sub exhaustive bad=%d" % bad)

    # nim: exhaustive m=1..3 over piles 1..15, sampled m=4.
    bad = 0
    for m in (1, 2, 3):
        for piles in itertools.product(range(1, 16), repeat=m):
            txt = "%d\n%s\n" % (m, " ".join(map(str, piles)))
            exp = ref_nim(list(piles))
            rc, out, err = call("nim", txt)
            checked += 1
            if rc != 0 or out != exp or err:
                bad += 1
                ok = False
                if bad <= 5:
                    print("FAIL nim", txt, repr(out), repr(exp))
    for piles in [(7, 3, 5, 6), (15, 15, 15, 15), (1, 2, 4, 8), (9, 9, 9, 9)]:
        txt = "4\n%s\n" % " ".join(map(str, piles))
        exp = ref_nim(list(piles))
        rc, out, err = call("nim", txt)
        checked += 1
        if rc != 0 or out != exp or err:
            bad += 1
            ok = False
            print("FAIL nim", txt, repr(out), repr(exp))
    print("nim exhaustive bad=%d" % bad)

    # wythoff: full 1..25 x 1..25.
    bad = 0
    for a in range(1, 26):
        for b in range(1, 26):
            txt = "%d %d\n" % (a, b)
            exp = ref_wythoff(a, b)
            rc, out, err = call("wythoff", txt)
            checked += 1
            if rc != 0 or out != exp or err:
                bad += 1
                ok = False
                if bad <= 8:
                    print("FAIL wythoff", txt, repr(out), repr(exp))
    print("wythoff exhaustive bad=%d" % bad)

    print("checked=%d" % checked)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
