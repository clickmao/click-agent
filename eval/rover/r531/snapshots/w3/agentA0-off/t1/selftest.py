"""Self-test: run acceptance form via python3 -m toolkit (subprocess), compare bytes.

sys.executable -c probe proved subprocess stdin/stdout piping works in this env
(b'{"a":1}' echoed back), so FAIL/ERR here are real module behaviour.
"""
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

VM = [
    ("1\nHALT", ""),
    ("3\nPUSH 5\nPUSH 3\nSUB\nPRINT\nHALT", "2"),
    ("4\nPUSH 2\nPUSH 3\nADD\nPRINT\nHALT", "5"),
    ("4\nPUSH 2\nPUSH 3\nMUL\nPRINT\nHALT", "6"),
    ("3\nPUSH 1\nPOP\nHALT", ""),
    ("3\nPOP\nPUSH 1\nHALT", "ERR"),
    ("2\nPUSH 1\nADD\nHALT", "ERR"),
    ("1\nDUP", "ERR"),
    ("3\nPUSH 1\nSWAP\nHALT", "ERR"),
    ("3\nPUSH 1\nJNZ 5\nHALT", "ERR"),
    ("0\n", "ERR"),
    ("65\n" + "HALT\n" * 65, "ERR"),
    ("2\nPUSH 1\nHALT", ""),
    ("2\nPUSH 1\nPUSH 2", "ERR"),
    ("3\nPUSH 0\nJNZ 2\nPUSH 7\nHALT", "7"),
    ("3\nPUSH 1\nJNZ 2\nPUSH 7\nHALT", "ERR"),
]

JSONM = [
    ("null", "null"),
    (" true ", "true"),
    ("false", "false"),
    ("123", "123"),
    ("-0", "0"),
    ("0", "0"),
    ("-45", "-45"),
    ("01", "ERR"),
    ("1.", "ERR"),
    ('"a\\nb"', '"a\\nb"'),
    ('"a\\tb"', '"a\\tb"'),
    ('"a\\\\b"', '"a\\\\b"'),
    ('"a\\"b"', '"a\\"b"'),
    ('"a\\/b"', '"a/b"'),
    ('"\\u0041"', '"A"'),
    ('"\\u001f"', "ERR"),
    ('"\\u0020"', '" "'),
    ('"\\uD83D"', '"\ud83d"'),
    ('"\\x41"', "ERR"),
    ('"abc', "ERR"),
    ('[1,2,3]', "[1,2,3]"),
    ("[]", "[]"),
    ("{}", "{}"),
    ('{"b":1,"a":2}', '{"a":2,"b":1}'),
    ('{"a":1,"b":[2,3]}', '{"a":1,"b":[2,3]}'),
    ('{"a":1,"a":2}', '{"a":2}'),
    ("[1,2", "ERR"),
    ("[1,2,]", "ERR"),
    ("{a:1}", "ERR"),
    ('{"a" 1}', "ERR"),
    ("", "ERR"),
    ("   ", "ERR"),
    ("1 2", "ERR"),
    ("1)", "ERR"),
    ("[1 2]", "ERR"),
]


def run(sub, data):
    p = subprocess.run(
        [sys.executable, "-m", "toolkit", sub],
        input=data.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
    )
    if p.stderr:
        raise AssertionError("stderr not silent for %r: %r" % (data, p.stderr))
    if p.returncode != 0:
        raise AssertionError("rc=%d for %r" % (p.returncode, data))
    return p.stdout.decode("utf-8")


def main():
    fails = []
    total = 0
    for data, want in VM:
        total += 1
        got = run("vm", data)
        if got != want:
            fails.append("FAIL vm %r -> %r want %r" % (data, got, want))
    for data, want in JSONM:
        total += 1
        got = run("jsonmini", data)
        if got != want:
            fails.append("FAIL json %r -> %r want %r" % (data, got, want))
    for m in fails:
        sys.stderr.write(m + "\n")
    sys.stderr.write("PASS %d/%d\n" % (total - len(fails), total))
    sys.stderr.write("FAIL\n" if fails else "ALL PASS\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
