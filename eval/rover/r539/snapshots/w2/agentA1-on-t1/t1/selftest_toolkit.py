# -*- coding: utf-8 -*-
"""Self-test driver: runs hidden-style cases through `python3 -m toolkit`.

Run from the workspace root:  python3 selftest_toolkit.py
Prints PASS/FAIL and exits 0 on pass / 1 on fail.
"""
import subprocess
import sys

NL = chr(10)


def run(sub, data):
    p = subprocess.run([sys.executable, "-m", "toolkit", sub],
                       input=data, capture_output=True, text=True)
    return p.stdout, p.stderr


CASES = [
    # vm
    ("vm", "5" + NL + "PUSH 2" + NL + "PUSH 3" + NL + "ADD" + NL + "PRINT" + NL + "HALT" + NL, "5"),
    ("vm", "1" + NL + "HALT" + NL, ""),
    ("vm", "2" + NL + "POP" + NL + "HALT" + NL, "ERR"),
    ("vm", "2" + NL + "PUSH 1" + NL + "POP" + NL, "ERR"),
    ("vm", "4" + NL + "PUSH 1" + NL + "JNZ 0" + NL + "PRINT" + NL + "HALT" + NL, "ERR"),
    ("vm", "3" + NL + "PUSH 0" + NL + "JNZ 9" + NL + "HALT" + NL, "ERR"),
    ("vm", "6" + NL + "PUSH 10" + NL + "PUSH 4" + NL + "SUB" + NL + "PRINT" + NL + "HALT" + NL + "POP" + NL, "6"),
    ("vm", "5" + NL + "PUSH 2" + NL + "DUP" + NL + "ADD" + NL + "PRINT" + NL + "HALT" + NL, "4"),
    ("vm", "6" + NL + "PUSH 1" + NL + "PUSH 2" + NL + "SWAP" + NL + "PRINT" + NL + "PRINT" + NL + "HALT" + NL, "1" + NL + "2"),
    ("vm", "4" + NL + "PUSH 5" + NL + "PUSH 6" + NL + "MUL" + NL + "HALT" + NL, ""),
    ("vm", "3" + NL + "ADD" + NL + "HALT" + NL + "PUSH 1" + NL, "ERR"),
    ("vm", "1" + NL + "SWAP" + NL, "ERR"),
    # jsonmini
    ("jsonmini", '{"b":[2,3],"a":1}' + NL, '{"a":1,"b":[2,3]}'),
    ("jsonmini", '  null  ', 'null'),
    ("jsonmini", '-0', '0'),
    ("jsonmini", '"a' + chr(92) + 'nb' + chr(92) + 't' + chr(92) + '"' + chr(92) + chr(92) + '"',
     '"a' + chr(92) + 'nb' + chr(92) + 't' + chr(92) + '"' + chr(92) + chr(92) + '"'),
    ("jsonmini", '{"a":1,"a":2}', '{"a":2}'),
    ("jsonmini", '01', 'ERR'),
    ("jsonmini", '1 2', 'ERR'),
    ("jsonmini", '', 'ERR'),
    ("jsonmini", '"' + chr(92) + 'u0041"', '"A"'),
    ("jsonmini", '"' + chr(92) + 'u001f"', 'ERR'),
    ("jsonmini", '{"k":true,"j":false,"z":null}', '{"j":false,"k":true,"z":null}'),
    ("jsonmini", '[[],[{}]]', '[[],[{}]]'),
    ("jsonmini", '[-0,12,-3]', '[0,12,-3]'),
    ("jsonmini", '[1,]', 'ERR'),
    ("jsonmini", '{"a":1,}', 'ERR'),
    ("jsonmini", 'truex', 'ERR'),
]


def main():
    fails = 0
    for sub, data, exp in CASES:
        out, err = run(sub, data)
        if out != exp or err != "":
            fails += 1
            print("FAIL", sub, repr(data), "got", repr(out), repr(err), "want", repr(exp))
    total = len(CASES)
    print("PASS" if fails == 0 else "FAIL", total - fails, "/", total)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
