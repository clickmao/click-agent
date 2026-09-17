import subprocess, sys, os

ROOT = os.path.dirname(os.path.abspath(__file__))

def run(sub, inp):
    p = subprocess.run([sys.executable, "-m", "toolkit", sub],
                       input=inp, capture_output=True, text=True, cwd=ROOT)
    return p.stdout, p.stderr, p.returncode

fails = 0
def T(name, sub, inp, exp):
    global fails
    out, err, rc = run(sub, inp)
    ok = (out == exp and err == "" and rc == 0)
    if not ok:
        fails += 1
        print("FAIL", name, repr(out), repr(err), rc)
    else:
        print("PASS", name)

T("vm_basic", "vm", "5\nPUSH 1\nPUSH 2\nADD\nPRINT\nHALT", "3")
T("vm_sub", "vm", "5\nPUSH 1\nPUSH 2\nSUB\nPRINT\nHALT", "-1")
T("vm_mul", "vm", "5\nPUSH 3\nPUSH 4\nMUL\nPRINT\nHALT", "12")
T("vm_dup_swap", "vm", "8\nPUSH 1\nPUSH 2\nSWAP\nPOP\nDUP\nPRINT\nPRINT\nHALT", "2\n2")
T("vm_jnz", "vm", "6\nPUSH 1\nJNZ 4\nPRINT 9\nPUSH 7\nPRINT\nHALT", "7")
T("vm_jnz_zero", "vm", "5\nPUSH 0\nJNZ 4\nPRINT\nHALT", "0")
T("vm_stackempty", "vm", "2\nPOP\nHALT", "ERR")
T("vm_underflow", "vm", "3\nPUSH 1\nADD\nHALT", "ERR")
T("vm_jump_oob", "vm", "2\nPUSH 1\nJNZ 5", "ERR")
T("vm_no_halt_overrun", "vm", "1\nPUSH 1", "ERR")
T("vm_infinite", "vm", "2\nPUSH 1\nJNZ 1", "ERR")
T("vm_halt_only", "vm", "1\nHALT", "")
T("vm_print_then_err", "vm", "3\nPUSH 5\nPRINT\nPOP", "ERR")

T("j_null", "jsonmini", " null ", "null")
T("j_bool", "jsonmini", "true\n", "true")
T("j_neg0", "jsonmini", "-0", "0")
T("j_int", "jsonmini", "-12", "-12")
T("j_leadzero", "jsonmini", "01", "ERR")
T("j_example", "jsonmini", '{"a":1,"b":[2,3]}', '{"a":1,"b":[2,3]}')
T("j_sort", "jsonmini", '{"b":1,"a":2}', '{"a":2,"b":1}')
T("j_dup", "jsonmini", '{"a":1,"a":2}', '{"a":2}')
T("j_esc", "jsonmini", '"a\\"b\\\\c\\/d\\ne\\tf"', '"a\\"b\\\\c/d\\ne\\tf"')
T("j_u", "jsonmini", '"\\u0041"', '"A"')
T("j_u_ctrl", "jsonmini", '"\\u001f"', "ERR")
T("j_ws_only", "jsonmini", "   \n  ", "ERR")
T("j_empty", "jsonmini", "", "ERR")
T("j_trailing", "jsonmini", "1 2", "ERR")
T("j_trailing2", "jsonmini", "truex", "ERR")
T("j_bad_esc", "jsonmini", '"\\q"', "ERR")
T("j_ctrl_raw", "jsonmini", '"a\nb"', "ERR")
T("j_nested", "jsonmini", ' { "x" : [ 1 , { "y" : "z" } ] } ', '{"x":[1,{"y":"z"}]}')
T("j_empty_arr", "jsonmini", "[]", "[]")
T("j_empty_obj", "jsonmini", "{}", "{}")
T("j_trailing_comma", "jsonmini", "[1,]", "ERR")
T("j_bare_key", "jsonmini", "{a:1}", "ERR")
T("j_plus", "jsonmini", "+1", "ERR")
T("j_neg_leadzero", "jsonmini", "-01", "ERR")

print("FAILS", fails)
sys.exit(1 if fails else 0)
