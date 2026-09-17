"""Self-test for the toolkit package. Run from the working root:

    python3 -m toolkit._selftest

Prints "PASS" or "FAIL: ..." and exits 0 on success, non-zero on failure.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

sys.path.insert(0, HERE)

import vm  # noqa: E402
import jsonmini  # noqa: E402


VM_CASES = [
    # (stdin, expected stdout)
    ("3\nPUSH 7\nPRINT\nHALT\n", "7"),
    ("5\nPUSH 1\nPUSH 2\nSUB\nPRINT\nHALT\n", "-1"),
    ("5\nPUSH 2\nPUSH 1\nSUB\nPRINT\nHALT\n", "1"),
    ("5\nPUSH 3\nPUSH 4\nMUL\nPRINT\nHALT\n", "12"),
    ("4\nPUSH 5\nDUP\nADD\nHALT\n", ""),
    ("5\nPUSH 1\nPUSH 2\nSWAP\nPRINT\nHALT\n", "1"),
    ("2\nPUSH 1\nPRINT\n", "ERR"),          # falls past last instruction
    ("1\nPOP\n", "ERR"),                    # pop empty
    ("2\nADD\nHALT\n", "ERR"),              # insufficient operands
    ("2\nPUSH 1\nJNZ 99\n", "ERR"),         # jump out of range
    ("3\nPUSH 1\nJNZ 0\nHALT\n", "ERR"),    # infinite loop -> step limit
    ("2\nPUSH -3\nPRINT\n", "ERR"),         # no HALT -> past end
    ("5\nPUSH 0\nJNZ 4\nPUSH 9\nPRINT\nHALT\n", "9"),  # JNZ not taken
    ("6\nPUSH 1\nJNZ 3\nPUSH 9\nPUSH 8\nPRINT\nHALT\n", "8"),
    ("4\nPUSH 4\nPUSH 5\nPOP\nHALT\n", ""),
    ("0\n", "ERR"),                         # k out of range
    ("abc\n", "ERR"),
]

JSON_CASES = [
    ("null", "null"),
    ("  true \n", "true"),
    ("false", "false"),
    ("0123", "ERR"),            # leading zero
    ("-0", "0"),
    ("-12", "-12"),
    ("1.", "ERR"),
    ('"a\\nb"', '"a\\nb"'),
    ('"a\\tb"', '"a\\tb"'),
    ('"a\\"b"', '"a\\"b"'),
    ('"a\\\\b"', '"a\\\\b"'),
    ('"a\\/b"', '"a/b"'),
    ('"\\u0041"', '"A"'),
    ('"\\u001f"', "ERR"),       # below 0x20
    ('"\\uZZZZ"', "ERR"),
    ('"\\q"', "ERR"),
    ('{"b":1,"a":2}', '{"a":2,"b":1}'),
    ('{"a":1,"a":2}', '{"a":2}'),
    ('[1,2,3]', "[1,2,3]"),
    (' { "a" : [ 2 , 3 ] , "b" : 1 } ', '{"a":[2,3],"b":1}'),
    ('{"a":1,"b":[2,3]}', '{"a":1,"b":[2,3]}'),
    ("", "ERR"),
    ("   ", "ERR"),
    ("1 2", "ERR"),
    ("[1,]", "ERR"),
    ('{"a":}', "ERR"),
    ("[1,2", "ERR"),
    ("", "ERR"),
]


def _run_cli(sub, stdin):
    p = subprocess.run(
        [sys.executable, "-m", "toolkit", sub],
        input=stdin.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
    )
    if p.stderr != b"":
        raise AssertionError("stderr not empty for %s: %r" % (sub, p.stderr))
    if p.returncode != 0:
        raise AssertionError("nonzero exit for %s: %d" % (sub, p.returncode))
    return p.stdout.decode("utf-8")


def main():
    try:
        for sub, cases in (("vm", VM_CASES), ("jsonmini", JSON_CASES)):
            for stdin, expected in cases:
                got = _run_cli(sub, stdin)
                if got != expected:
                    print("FAIL: %s stdin=%r expected=%r got=%r" % (sub, stdin, expected, got))
                    return 1
        # direct solve() parity (no newline appended)
        assert vm.solve("3\nPUSH 7\nPRINT\nHALT\n") == "7"
        assert jsonmini.solve('{"a":1}') == '{"a":1}'
        print("PASS")
        return 0
    except AssertionError as e:
        print("FAIL: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
