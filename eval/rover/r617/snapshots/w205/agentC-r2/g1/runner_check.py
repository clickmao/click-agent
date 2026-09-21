import subprocess

CASES = {
    'life': [
        ("11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n",
         ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."),
        ("11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n",
         "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."),
    ],
    'sub': [
        ("31 3\n1 6 10\n", "WIN 6"),
        ("19 1\n1\n", "WIN 1"),
    ],
    'nim': [
        ("3\n5 9 4\n", "WIN 2 8"),
        ("1\n3\n", "WIN 1 3"),
    ],
    'wythoff': [
        ("21 25\n", "WIN 15 15"),
        ("10 9\n", "WIN 0 3"),
    ],
}

ok = True
for game, cases in CASES.items():
    for inp, exp in cases:
        r = subprocess.run(['python3', '-m', 'games', game], input=inp,
                           capture_output=True, text=True)
        got = r.stdout.rstrip('\n')
        if r.returncode != 0 or got != exp or r.stderr != '':
            ok = False
            print('FAIL', game, repr(inp[:12]), 'rc=', r.returncode, 'stderr=', repr(r.stderr), 'got=', repr(got), 'exp=', repr(exp))
        else:
            print('PASS', game, repr(inp[:12]))
print('ALL_PASS' if ok else 'SOME_FAIL')
