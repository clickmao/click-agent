import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VM_CASES = [
    # every non-error program MUST HALT (falling past last instr = ERR)
    ("4\nPUSH 1\nPUSH 2\nPRINT\nHALT\n", "2"),
    ("5\nPUSH 10\nPUSH 3\nSUB\nPRINT\nHALT\n", "7"),
    ("5\nPUSH 2\nPUSH 3\nMUL\nPRINT\nHALT\n", "6"),
    ("5\nPUSH 1\nPUSH 2\nADD\nPRINT\nHALT\n", "3"),
    ("5\nPUSH 5\nDUP\nADD\nPRINT\nHALT\n", "10"),
    ("6\nPUSH 1\nPUSH 2\nSWAP\nPRINT\nPRINT\nHALT\n", "1\n2"),
    # JNZ not taken -> falls through to PUSH 9 / PRINT / HALT
    ("7\nPUSH 0\nJNZ 4\nPUSH 9\nPRINT\nHALT\nPOP\n", "9"),
    # JNZ taken -> jumps to HALT at addr 4 -> empty output
    ("7\nPUSH 1\nJNZ 4\nPUSH 9\nPRINT\nHALT\nPOP\n", ""),
    # loop body: keep value on stack, only compute copy for the test
    # 0 PUSH 3 / 1 PRINT / 2 PUSH 1 / 3 SUB  -> wait: PRINT pops. Redesign:
    # 0 PUSH 3 / 1 DUP / 2 PRINT / 3 PUSH 1 / 4 SUB / 5 DUP / 6 JNZ 1 / 7 POP / 8 HALT
    ("9\nPUSH 3\nDUP\nPRINT\nPUSH 1\nSUB\nDUP\nJNZ 1\nPOP\nHALT\n", "3\n2\n1"),
    ("2\nPUSH 1\nPUSH 2\n", "ERR"),          # no HALT, runs past end
    ("4\nPUSH 1\nPRINT\nHALT\nPRINT\n", "1"),  # HALT stops before 2nd PRINT
    ("1\nPOP\n", "ERR"),                     # underflow
    ("2\nPUSH 1\nADD\n", "ERR"),             # too few operands
    ("2\nPUSH 1\nJNZ 99\n", "ERR"),          # jump out of range
    ("3\nPUSH 1\nJNZ 5\nPRINT\n", "ERR"),    # taken jump past end -> ERR
    ("3\nPUSH 0\nJNZ 5\nHALT\n", ""),        # jump not taken, addr never used
    ("2\nPUSH 1\nNOPE\n", "ERR"),            # unknown opcode
    ("1\nPUSH\n", "ERR"),                    # missing operand
    ("0\n", "ERR"),                          # k out of range
    ("1\nHALT\n", ""),                       # minimal ok -> empty
]

JSON_CASES = [
    ("null", "null"),
    ("true", "true"),
    ("false", "false"),
    (" 42 ", "42"),
    ("-0", "0"),
    ("-12", "-12"),
    ("0", "0"),
    ('"a\\"b"', '"a\\"b"'),
    ('"a\\\\b"', '"a\\\\b"'),
    ('"a\\/b"', '"a/b"'),
    ('"a\\nb"', '"a\\nb"'),
    ('"a\\tb"', '"a\\tb"'),
    ('"\\u0041"', '"A"'),
    ('"\\u0020"', '" "'),
    ("[]", "[]"),
    ("[1,2,3]", "[1,2,3]"),
    (" {} ", "{}"),
    ('{"b":1,"a":2}', '{"a":2,"b":1}'),
    ('{"a":1,"b":[2,3]}', '{"a":1,"b":[2,3]}'),
    ('{"a":1,"a":2}', '{"a":2}'),
    ('{"a":{"c":1,"b":2}}', '{"a":{"b":2,"c":1}}'),
    (' [ 1 , { "x" : [ true , null ] } ] ', '[1,{"x":[true,null]}]'),
    ("", "ERR"),
    ("   ", "ERR"),
    ("01", "ERR"),
    ("-", "ERR"),
    ("1 2", "ERR"),
    ("[1,2", "ERR"),
    ('{"a":1,}', "ERR"),
    ("{a:1}", "ERR"),
    ('"\\u001f"', "ERR"),
    ('"\\x41"', "ERR"),
    ('"unterminated', "ERR"),
    ("nul", "ERR"),
    ("1.5", "ERR"),
    ("[1,]", "ERR"),
    ('{"a" 1}', "ERR"),
]


def run(sub, stdin_text):
    p = subprocess.run(
        [sys.executable, "-m", "toolkit", sub],
        input=stdin_text, capture_output=True, text=True, cwd=ROOT,
    )
    return p.returncode, p.stdout, p.stderr


def main():
    ok = True
    for stdin_text, expected in VM_CASES:
        rc, out, err = run("vm", stdin_text)
        if not (rc == 0 and out == expected and err == ""):
            ok = False
            print("FAIL [vm] in=%r expected=%r got=%r rc=%d err=%r"
                  % (stdin_text, expected, out, rc, err))
    for stdin_text, expected in JSON_CASES:
        rc, out, err = run("jsonmini", stdin_text)
        if not (rc == 0 and out == expected and err == ""):
            ok = False
            print("FAIL [jsonmini] in=%r expected=%r got=%r rc=%d err=%r"
                  % (stdin_text, expected, out, rc, err))
    # negative control: swap in a broken solve, a real case must flip to ERR
    sys.path.insert(0, ROOT)
    from toolkit import vm as vmm
    real = vmm.solve
    vmm.solve = lambda t: "ERR"
    rc, out, err = run("vm", "5\nPUSH 1\nPUSH 2\nADD\nPRINT\nHALT\n")
    vmm.solve = real
    if out != "ERR":
        ok = False
        print("FAIL negative control not detected")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
