import subprocess, sys
cases = {
"life": [("11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n",
".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."),
("11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n",
"##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n..")],
"sub": [("31 3\n1 6 10\n","WIN 6"),("19 1\n1\n","WIN 1")],
"nim": [("3\n5 9 4\n","WIN 2 8"),("1\n3\n","WIN 1 3")],
"wythoff": [("21 25\n","WIN 15 15"),("10 9\n","WIN 0 3")],
}
ok=True
for g,cs in cases.items():
    for i,(inp,exp) in enumerate(cs):
        p=subprocess.run([sys.executable,"-m","games",g],input=inp,capture_output=True,text=True)
        good=(p.stdout==exp and p.returncode==0 and p.stderr=="")
        ok &= good
        print(g,i,"OK" if good else "FAIL","rc",p.returncode,"err",repr(p.stderr))
        if not good:
            print(" got",repr(p.stdout)); print(" exp",repr(exp))
print("ALL PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
