"""mathkit 自检 (无头, 非交互)。运行: python3 selftest_mathkit.py"""
import json
import subprocess
import sys

CASES = [
    ("qr_count", {"a": 11, "m": 16}, "0"),
    ("choose", {"n": 18, "k": 7, "mod": 97}, "8"),
    ("det", {"matrix": [[-2, 0], [-1, -6]], "mod": 101}, "12"),
    ("shortest", {"matrix": [[0, 0, 5, 1, 0], [0, 0, 1, 9, 6], [5, 1, 0, 0, 0],
                             [1, 9, 0, 0, 4], [0, 6, 0, 4, 0]], "src": 0, "dst": 4}, "5"),
    ("expect", {"red": 1, "blue": 3, "draw": 3}, "3/4"),
    # 额外边界/负向用例
    ("qr_count", {"a": 1, "m": 16}, "4"),      # x=1,7,9,15 -> 4 解
    ("qr_count", {"a": 0, "m": 16}, "4"),      # x=0,4,8,12
    ("choose", {"n": 0, "k": 0, "mod": 97}, "1"),
    ("choose", {"n": 40, "k": 20, "mod": 1000003}, str(__import__("math").comb(40, 20) % 1000003)),
    ("det", {"matrix": [[1, 2], [3, 4]], "mod": 97}, str(-2 % 97)),
    ("det", {"matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]], "mod": 97}, "0"),
    ("det", {"matrix": [[2, 0, 0, 0], [0, 3, 0, 0], [0, 0, 4, 0], [0, 0, 0, 5]], "mod": 97}, str(120 % 97)),
    ("shortest", {"matrix": [[0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], "src": 0, "dst": 3}, "-1"),
    ("shortest", {"matrix": [[0, 2, 0, 0], [2, 0, 3, 0], [0, 3, 0, 0], [0, 0, 0, 0]], "src": 0, "dst": 2}, "5"),
    ("shortest", {"matrix": [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], "src": 2, "dst": 2}, "0"),
    ("expect", {"red": 3, "blue": 3, "draw": 6}, "3/1"),
    ("expect", {"red": 6, "blue": 1, "draw": 1}, "6/7"),
    ("expect", {"red": 2, "blue": 4, "draw": 3}, "1/1"),
]

failed = 0
for op, args, want in CASES:
    p = subprocess.run([sys.executable, "-m", "mathkit", op],
                       input=json.dumps(args), text=True,
                       capture_output=True)
    got = p.stdout
    ok = (got == want) and (p.returncode == 0) and (p.stderr == "")
    if not ok:
        failed += 1
    print(f"[{'PASS' if ok else 'FAIL'}] {op} {args} -> {got!r} (want {want!r}) rc={p.returncode} err={p.stderr!r}")

print("RESULT:", "PASS" if failed == 0 else f"FAIL({failed})")
sys.exit(1 if failed else 0)
