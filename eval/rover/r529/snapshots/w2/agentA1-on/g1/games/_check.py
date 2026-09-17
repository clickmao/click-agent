import subprocess, sys, os

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
for g, inp, exp in cases:
    r = subprocess.run([sys.executable, "-m", "games", g], input=inp.encode(),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    got = r.stdout.decode()
    good = got == exp and r.stderr == b"" and r.returncode == 0
    ok = ok and good
    print(g, "PASS" if good else "FAIL", repr(got), "err=", r.stderr[:60])
print("ALL PASS" if ok else "SOME FAIL")
sys.exit(0 if ok else 1)
