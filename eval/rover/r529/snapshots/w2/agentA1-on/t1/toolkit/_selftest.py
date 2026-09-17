import subprocess, sys
def run(sub, inp):
    p = subprocess.run([sys.executable, "-m", "toolkit", sub], input=inp,
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr
cases = []
cases.append(("vm", "3\nPUSH 5\nPRINT\nHALT\n", (0, "5", "")))
cases.append(("vm", "1\nPOP\n", (0, "ERR", "")))
cases.append(("vm", "2\nPUSH 1\nPRINT\n", (0, "ERR", "")))
cases.append(("vm", "3\nPUSH 7\nJNZ 99\nHALT\n", (0, "ERR", "")))
cases.append(("vm", "2\nPUSH 1\nDUP\n", (0, "ERR", "")))
cases.append(("vm", "6\nPUSH 3\nPUSH 4\nADD\nPRINT\nHALT\nPOP\n", (0, "7", "")))
cases.append(("vm", "5\nPUSH 10\nPUSH 3\nSUB\nPRINT\nHALT\n", (0, "7", "")))
cases.append(("vm", "5\nPUSH 10\nPUSH 3\nSWAP\nSUB\nPRINT\nHALT\n", (0, "3", "")))
cases.append(("vm", "1\nHALT\n", (0, "", "")))
cases.append(("vm", "2\nPUSH 1\nJNZ 1\n", (0, "ERR", "")))
cases.append(("jsonmini", '{"a":1,"b":[2,3]}', (0, '{"a":1,"b":[2,3]}', "")))
cases.append(("jsonmini", '  \n true \n', (0, "true", "")))
cases.append(("jsonmini", '-0', (0, "0", "")))
cases.append(("jsonmini", '01', (0, "ERR", "")))
cases.append(("jsonmini", '"a\\nb"', (0, '"a\\nb"', "")))
cases.append(("jsonmini", '"\\u0041"', (0, '"A"', "")))
cases.append(("jsonmini", '"\\u001f"', (0, "ERR", "")))
cases.append(("jsonmini", '{"b":1,"a":2,"a":3}', (0, '{"a":3,"b":1}', "")))
cases.append(("jsonmini", '1 2', (0, "ERR", "")))
cases.append(("jsonmini", '', (0, "ERR", "")))
cases.append(("jsonmini", '[1,2,]', (0, "ERR", "")))
cases.append(("jsonmini", '"bad\\x"', (0, "ERR", "")))
fail = 0
for sub, inp, exp in cases:
    got = run(sub, inp)
    if got != exp:
        fail += 1
        print("FAIL", sub, repr(inp), "got", got, "exp", exp)
print("PASS" if fail == 0 else "FAIL", "total", len(cases), "failed", fail)
sys.exit(1 if fail else 0)
