import subprocess, sys

def run(sub, inp):
    p = subprocess.run([sys.executable, "-m", "toolkit", sub], input=inp,
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

cases = []
vm = [
    ("3\nPUSH 1\nPUSH 2\nPRINT\n", "2"),
    ("4\nPUSH 10\nPUSH 3\nSUB\nPRINT\n", "7"),
    ("5\nPUSH 2\nPUSH 3\nMUL\nDUP\nPRINT\n", "6"),
    ("3\nPUSH 1\nPOP\nPOP\n", "ERR"),
    ("1\nPUSH 5\n", "ERR"),
    ("2\nPUSH 7\nHALT\n", ""),
    ("3\nPUSH 0\nJNZ 5\nPRINT\n", "0"),
    ("3\nPUSH 1\nJNZ 5\nPRINT\n", "ERR"),
    ("4\nPUSH 1\nPUSH 2\nSWAP\nPRINT\n", "1"),
    ("2\nPOP\nHALT\n", "ERR"),
    ("1\nNOP\n", "ERR"),
]
for inp, exp in vm:
    rc, out, err = run("vm", inp)
    cases.append(("vm", repr(inp[:25]), exp, out, out == exp and err == "" and rc == 0))

js = [
    ('{"a":1,"b":[2,3]}', '{"a":1,"b":[2,3]}'),
    ('  null  ', 'null'),
    ('-0', '0'),
    ('[1,2,{"z":0,"a":1}]', '[1,2,{"a":1,"z":0}]'),
    ('{"b":1,"a":2,"b":3}', '{"a":2,"b":3}'),
    ('"a\\nb"', '"a\\nb"'),
    ('"\\u0041"', '"A"'),
    ('"\\u001f"', 'ERR'),
    ('01', 'ERR'),
    ('', 'ERR'),
    ('{"a":1} x', 'ERR'),
    ('[1,]', 'ERR'),
    ('"a\\/b"', '"a/b"'),
    ('123', '123'),
    ('-12', '-12'),
    ('[]', '[]'),
    ('{}', '{}'),
    ('trve', 'ERR'),
    ('"\\t"', '"\\t"'),
    ('"a"', '"a"'),
    ('true', 'true'),
    ('false', 'false'),
    ('[1,2,3]', '[1,2,3]'),
    ('{"a":{"b":{"c":1}}}', '{"a":{"b":{"c":1}}}'),
]
for inp, exp in js:
    rc, out, err = run("jsonmini", inp)
    cases.append(("json", repr(inp), exp, out, out == exp and err == "" and rc == 0))

bad = [c for c in cases if not c[-1]]
for c in cases:
    print(("PASS" if c[-1] else "FAIL"), c[0], c[1], "exp=", repr(c[2]), "got=", repr(c[3]))
print("TOTAL", len(cases), "FAIL", len(bad))
