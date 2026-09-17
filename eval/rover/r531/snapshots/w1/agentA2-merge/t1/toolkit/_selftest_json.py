import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
    for stdin_text, expected in JSON_CASES:
        rc, out, err = run("jsonmini", stdin_text)
        if not (rc == 0 and out == expected and err == ""):
            ok = False
            print("FAIL [jsonmini] in=%r expected=%r got=%r rc=%d err=%r"
                  % (stdin_text, expected, out, rc, err))
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
