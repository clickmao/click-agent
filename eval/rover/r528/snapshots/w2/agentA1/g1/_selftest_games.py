import io, sys, subprocess, os, itertools, functools, random

def run(gid, payload):
    p = subprocess.run([sys.executable, '-m', 'games', gid], input=payload,
                       capture_output=True, text=True, cwd=os.getcwd())
    return p.stdout, p.stderr, p.returncode

cases = [
 ('life', "11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n",
  ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."),
 ('life', "11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n",
  "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."),
 ('sub', "31 3\n1 6 10\n", "WIN 6"),
 ('sub', "19 1\n1\n", "WIN 1"),
 ('nim', "3\n5 9 4\n", "WIN 2 8"),
 ('nim', "1\n3\n", "WIN 1 3"),
 ('wythoff', "21 25\n", "WIN 15 15"),
 ('wythoff', "10 9\n", "WIN 0 3"),
]

fails = 0
for gid, inp, exp in cases:
    out, err, rc = run(gid, inp)
    ok = (out == exp) and (err == '') and (rc == 0)
    if not ok:
        fails += 1
        print("FAIL", gid, repr(out), repr(exp), repr(err), rc)
print("public cases:", len(cases) - fails, "/", len(cases), "PASS" if fails == 0 else "FAIL")

from games import wythoff as W, sub as S, nim as N

@functools.lru_cache(maxsize=None)
def wt_cold(a, b):
    if a == 0 and b == 0:
        return True
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if wt_cold(a - i, b - j):
                return False
    return True

wt_fail = 0
for a in range(1, 26):
    for b in range(1, 26):
        cold = wt_cold(a, b)
        got = W.solve("%d %d" % (a, b))
        if cold:
            if got != 'LOSE':
                wt_fail += 1
        else:
            parts = got.split()
            assert parts[0] == 'WIN', (a, b, got)
            i, j = int(parts[1]), int(parts[2])
            legal = ((i == 0) ^ (j == 0)) or (i == j and i > 0)
            assert legal and i <= a and j <= b and not (i == 0 and j == 0), (a, b, got)
            assert wt_cold(a - i, b - j), (a, b, got)
            for ii in range(i + 1):
                for jj in range(b + 1):
                    if ii == 0 and jj == 0: continue
                    if ii != 0 and jj != 0 and ii != jj: continue
                    if ii < i or (ii == i and jj < j):
                        if wt_cold(a - ii, b - jj):
                            raise AssertionError(("not minimal", a, b, got, ii, jj))
print("wythoff brute-force:", "PASS" if wt_fail == 0 else "FAIL", wt_fail)

def sub_ref(n, moves):
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in moves)
    if not win[n]:
        return 'LOSE'
    return 'WIN %d' % min(s for s in moves if s <= n and not win[n - s])

sub_fail = 0; sub_tested = 0
for n in range(1, 81):
    for k in range(1, 13):
        for _ in range(6):
            pool = sorted([1] + random.sample(range(2, 13), k - 1)) if k > 1 else [1]
            got = S.solve("%d %d\n%s\n" % (n, k, ' '.join(map(str, pool))))
            exp = sub_ref(n, pool)
            sub_tested += 1
            if got != exp:
                sub_fail += 1
                print("SUBFAIL", n, pool, got, exp)
print("sub brute-force:", "PASS" if sub_fail == 0 else "FAIL", "tested=%d" % sub_tested)

def nim_ref(piles):
    x = 0
    for a in piles: x ^= a
    if x == 0: return 'LOSE'
    for i, a in enumerate(piles):
        t = a ^ x
        if t < a: return 'WIN %d %d' % (i + 1, a - t)
    return 'LOSE'

nim_fail = 0; nim_tested = 0
for m in range(1, 5):
    for piles in itertools.product(range(1, 16), repeat=m):
        got = N.solve("%d\n%s\n" % (m, ' '.join(map(str, piles))))
        exp = nim_ref(list(piles))
        nim_tested += 1
        if got != exp:
            nim_fail += 1
            print("NIMFAIL", piles, got, exp)
print("nim brute-force:", "PASS" if nim_fail == 0 else "FAIL", "tested=%d" % nim_tested)

# life: compare against a naive independent implementation on random grids
def life_naive(h, w, k, rows):
    g = [list(r) for r in rows]
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                c = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0: continue
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < h and 0 <= xx < w and g[yy][xx] == '#':
                            c += 1
                nxt[y][x] = '#' if (g[y][x] == '#' and c in (2, 3)) or (g[y][x] == '.' and c == 3) else '.'
        g = nxt
    return '\n'.join(''.join(r) for r in g)

import games.life as L
life_fail = 0; life_tested = 0
for _ in range(200):
    h = random.randint(1, 8); w = random.randint(1, 8); k = random.randint(0, 6)
    rows = [''.join(random.choice('.#') for _ in range(w)) for _ in range(h)]
    payload = "%d %d %d\n%s\n" % (h, w, k, '\n'.join(rows))
    got = L.solve(payload)
    exp = life_naive(h, w, k, rows)
    life_tested += 1
    if got != exp:
        life_fail += 1
        print("LIFEFAIL", payload, repr(got), repr(exp))
print("life brute-force:", "PASS" if life_fail == 0 else "FAIL", "tested=%d" % life_tested)

# CLI silence + k=0 identity
out, err, rc = run('life', "1 1 0\n#\n")
print("cli-silence/k0:", "PASS" if (out == '#' and err == '' and rc == 0) else "FAIL")

allok = fails == 0 and wt_fail == 0 and sub_fail == 0 and nim_fail == 0 and life_fail == 0
print("SELFTEST", "PASS" if allok else "FAIL")
sys.exit(0 if allok else 1)
