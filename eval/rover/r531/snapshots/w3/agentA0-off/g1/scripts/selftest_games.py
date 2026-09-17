import subprocess, sys
sys.path.insert(0, '.')
from games.wythoff import solve as wsolve

CASES = {
 'life': [
  ("11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#",
   ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."),
  ("11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#",
   "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."),
 ],
 'sub': [("31 3\n1 6 10", "WIN 6"), ("19 1\n1", "WIN 1")],
 'nim': [("3\n5 9 4", "WIN 2 8"), ("1\n3", "WIN 1 3")],
 'wythoff': [("21 25", "WIN 15 15"), ("10 9", "WIN 0 3")],
}
fails = 0
for gid, cases in CASES.items():
    for i, (inp, exp) in enumerate(cases):
        p = subprocess.run([sys.executable, '-m', 'games', gid],
                           input=inp, capture_output=True, text=True)
        ok = p.returncode == 0 and p.stdout == exp and p.stderr == ''
        print("%-8s case%d rc=%d match=%s stderr=%r" % (gid, i, p.returncode, p.stdout == exp, p.stderr))
        if not ok:
            fails += 1; print("  exp=%r\n  got=%r" % (exp, p.stdout))

def ref_losing(a, b):
    if a > b: a, b = b, a
    d = b - a
    n = int(d * (1 + 5**0.5) / 2)
    for c in (n-2, n-1, n, n+1, n+2):
        if c >= 0 and c == a and c + d == b: return True
    return False

bad = 0
for a in range(1, 26):
    for b in range(1, 26):
        s = wsolve("%d %d" % (a, b))
        if s == 'LOSE':
            if not ref_losing(a, b): bad += 1; print("LOSE mismatch", a, b)
        else:
            _, i, j = s.split(); i, j = int(i), int(j)
            legal = (i == 0) or (j == 0) or (i == j)
            if not (legal and i <= a and j <= b and (i or j) and ref_losing(a - i, b - j)):
                bad += 1; print("move bad", a, b, s)
print("wythoff exhaustive bad =", bad)
print("FAILS", fails)
sys.exit(1 if (fails or bad) else 0)
