import math
import subprocess
import sys

cases = [
    ("qr_count", '{"a": 11, "m": 16}', "0"),
    ("choose", '{"n": 18, "k": 7, "mod": 97}', "8"),
    ("det", '{"matrix": [[-2, 0], [-1, -6]], "mod": 101}', "12"),
    ("shortest", '{"matrix": [[0,0,5,1,0],[0,0,1,9,6],[5,1,0,0,0],[1,9,0,0,4],[0,6,0,4,0]], "src": 0, "dst": 4}', "5"),
    ("expect", '{"red": 1, "blue": 3, "draw": 3}', "3/4"),
    ("qr_count", '{"a": 0, "m": 8}', "2"),
    ("choose", '{"n": 40, "k": 20, "mod": 1000003}', str(math.comb(40, 20) % 1000003)),
    ("det", '{"matrix": [[1,2,3,4],[5,6,7,8],[9,10,11,12],[13,14,15,16]], "mod": 97}', "0"),
    ("shortest", '{"matrix": [[0,1,0,0],[1,0,0,0],[0,0,0,1],[0,0,1,0]], "src": 0, "dst": 3}', "-1"),
    ("expect", '{"red": 3, "blue": 3, "draw": 6}', "3/1"),
]

bad = 0
for op, inp, exp in cases:
    p = subprocess.run([sys.executable, "-m", "mathkit", op], input=inp,
                       capture_output=True, text=True)
    if p.stdout != exp or p.returncode != 0 or p.stderr != "":
        bad += 1
        print("FAIL", op, repr(inp), "got", repr(p.stdout), "exp", repr(exp),
              "rc", p.returncode, "err", repr(p.stderr))
print("PASS" if bad == 0 else "FAIL", len(cases) - bad, "/", len(cases))
