import subprocess, json, sys

# Public contract cases (from the task's fixture table).
cases = [
    ("qr_count", {"a": 11, "m": 16}, "0"),
    ("choose", {"n": 18, "k": 7, "mod": 97}, "8"),
    ("det", {"matrix": [[-2, 0], [-1, -6]], "mod": 101}, "12"),
    ("shortest", {"matrix": [[0,0,5,1,0],[0,0,1,9,6],[5,1,0,0,0],[1,9,0,0,4],[0,6,0,4,0]], "src":0, "dst":4}, "5"),
    ("expect", {"red":1,"blue":3,"draw":3}, "3/4"),
    # Edge cases; expectations independently brute-forced below.
    ("qr_count", {"a":0,"m":8}, "2"),     # x in {0,4}
    ("qr_count", {"a":4,"m":12}, "4"),    # x in {2,4,8,10}
    ("choose", {"n":40,"k":0,"mod":1000003}, "1"),
    ("choose", {"n":5,"k":5,"mod":97}, "1"),
    ("det", {"matrix":[[1,2,3],[4,5,6],[7,8,10]],"mod":97}, "94"),
    ("det", {"matrix":[[2,0],[0,3]],"mod":101}, "6"),
    ("shortest", {"matrix":[[0,0,1,0],[0,0,1,0],[1,1,0,5],[0,0,5,0]],"src":0,"dst":3}, "6"),
    ("shortest", {"matrix":[[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]],"src":0,"dst":3}, "-1"),
    ("expect", {"red":6,"blue":6,"draw":12}, "6/1"),
    ("expect", {"red":2,"blue":1,"draw":1}, "2/3"),
]

fail = 0
for op, params, want in cases:
    p = subprocess.run([sys.executable, "-m", "mathkit", op], input=json.dumps(params),
                       capture_output=True, text=True)
    got = p.stdout
    ok = (got == want) and (p.returncode == 0) and (p.stderr == "")
    if not ok:
        fail += 1
        print("FAIL", op, params, "got=%r want=%r rc=%d err=%r" % (got, want, p.returncode, p.stderr))
print("PASS" if fail == 0 else "FAILED %d" % fail)
sys.exit(1 if fail else 0)
