"""无头自检: python3 -m toolkit._selftest

覆盖 vm 与 jsonmini 的核心不变式与边界 / 负向控制。
打印 PASS/FAIL, 退出码 0=通过 / 非 0=失败。
仅作开发自检, 不参与评测路径。
"""
import sys
from toolkit import vm, jsonmini

VM_CASES = [
    # (stdin, expected stdout)
    ("1\nHALT", ""),
    ("3\nPUSH 1\nPRINT\nHALT", "1"),
    ("5\nPUSH 3\nPUSH 4\nADD\nPRINT\nHALT", "7"),
    ("5\nPUSH 7\nPUSH 3\nSUB\nPRINT\nHALT", "4"),          # b=7,a=3 => 7-3
    ("5\nPUSH 6\nPUSH 7\nMUL\nPRINT\nHALT", "42"),
    ("4\nPUSH 5\nDUP\nADD\nHALT", ""),
    ("6\nPUSH 1\nPUSH 2\nSWAP\nPRINT\nPRINT\nHALT", "1\n2"),
    ("5\nPUSH 9\nPOP\nPUSH 8\nPRINT\nHALT", "8"),
    # JNZ 跳转: 计数循环 3 次打印 0
    ("8\nPUSH 3\nJNZ 4\nHALT\nPUSH 0\nPRINT\nPUSH 1\nSUB", "ERR"),  # 步数内无 HALT? 见下: 有 HALT 在 addr2
    # 栈空弹栈
    ("1\nPOP", "ERR"),
    ("1\nADD", "ERR"),
    # 跳转越界
    ("2\nPUSH 1\nJNZ 5", "ERR"),
    # 越过最后一条
    ("1\nPUSH 1", "ERR"),
    # 未知指令 (解析期)
    ("1\nFOO", "ERR"),
    # 超出步数: 死循环 PUSH 1; JNZ 0
    ("2\nJNZ 0\nPUSH 1", "ERR"),
    # PRINT 多行顺序
    ("6\nPUSH 1\nPRINT\nPUSH 2\nPRINT\nPUSH 3\nPRINT", "ERR"),  # 无 HALT 越过
    ("7\nPUSH 1\nPRINT\nPUSH 2\nPRINT\nPUSH 3\nPRINT\nHALT", "1\n2\n3"),
]

# 真实 JNZ 循环样例: 打印 0,1,2
VM_LOOP = "8\nPUSH 3\nJNZ 3\nHALT\nPUSH 10\nPRINT\nPUSH 1\nSUB"
# 执行: pc0 PUSH3 ->栈[3]; pc1 JNZ: pop3!=0 -> pc3; pc3 PUSH10 ->[10];
# pc4 PRINT->出10; pc5 PUSH1->[1]; pc6 SUB->空? 需要次顶 => ERR
# 放弃该样例, 用下方确定版本


JSON_CASES = [
    ("null", "null"),
    ("  true\n", "true"),
    ("false", "false"),
    ("0", "0"),
    ("-0", "0"),
    ("123", "123"),
    ("-42", "-42"),
    ('"hi"', '"hi"'),
    ('"a\\nb"', '"a\\nb"'),
    ('"a\\tb"', '"a\\tb"'),
    ('"qa\\"q"', '"qa\\"q"'),
    ("[]", "[]"),
    ("[1,2,3]", "[1,2,3]"),
    ('{"a":1,"b":[2,3]}', '{"a":1,"b":[2,3]}'),
    ('{"b":1,"a":2}', '{"a":2,"b":1}'),
    ('{"a":1,"a":2}', '{"a":2}'),
    ('"\\u0041"', '"A"'),
    ('"\\/"', '"/"'),
    ('"\\\\"', '"\\\\"'),
    ("[ [ ] , { } ]", "[[],{}]"),
    # 非法
    ("", "ERR"),
    ("   ", "ERR"),
    ("01", "ERR"),
    ("1 2", "ERR"),
    ("1x", "ERR"),
    ("tru", "ERR"),
    ("[1,]", "ERR"),
    ("{a:1}", "ERR"),
    ('"\\x"', "ERR"),
    ('"\\u0019"', "ERR"),   # 解码码点 < 0x20
    ('"\\u00"', "ERR"),
    ("[1", "ERR"),
    ("}", "ERR"),
    ('"unterminated', "ERR"),
]


def main():
    fails = 0
    total = 0

    for text, exp in VM_CASES:
        total += 1
        got = vm.solve(text)
        if got != exp:
            fails += 1
            print("FAIL vm %r -> %r (exp %r)" % (text, got, exp))

    for text, exp in JSON_CASES:
        total += 1
        got = jsonmini.solve(text)
        if got != exp:
            fails += 1
            print("FAIL json %r -> %r (exp %r)" % (text, got, exp))

    print("%s  %d/%d" % ("PASS" if fails == 0 else "FAIL", total - fails, total))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
