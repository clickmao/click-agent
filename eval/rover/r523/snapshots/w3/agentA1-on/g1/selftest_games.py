import subprocess, sys, os, math

E = os.environ.copy()
E["PYTHONPATH"] = "."
cases = [
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
ok = True
for gid, inp, exp in cases:
    p = subprocess.run([sys.executable, "-m", "games", gid], input=inp,
                       capture_output=True, text=True, env=E)
    good = (p.stdout == exp)
    ok &= good and p.returncode == 0 and p.stderr == ""
    print(("PASS" if good else "FAIL"), gid, "rc=", p.returncode,
          "stderr_len=", len(p.stderr), "" if good else repr(p.stdout))
print("ALL", "PASS" if ok else "FAIL")

phi = (1 + 5 ** 0.5) / 2
bad = 0
d = 1
while True:
    a = math.floor(d * phi)
    b = a + d
    if b > 25:
        break
    p = subprocess.run([sys.executable, "-m", "games", "wythoff"],
                       input="{} {}\n".format(a, b), capture_output=True, text=True, env=E)
    if p.stdout != "LOSE":
        bad += 1
        print("NEG-FAIL", a, b, repr(p.stdout))
    d += 1
print("neg_control_bad=", bad)
