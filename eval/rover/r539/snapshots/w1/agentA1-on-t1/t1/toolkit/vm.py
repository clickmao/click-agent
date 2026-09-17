"""vm_run: 栈式虚拟机解释器。

solve(text) 接收完整 stdin 文本, 返回应当写出的 stdout 文本 (末尾不带换行)。
非法情况输出单行 "ERR"。
"""
from __future__ import annotations


def solve(text: str) -> str:
    lines = text.split("\n")
    # 允许结尾空行
    while lines and lines[-1] == "":
        lines.pop()

    if not lines:
        return "ERR"
    try:
        k = int(lines[0].strip())
    except ValueError:
        return "ERR"
    if k < 1 or k > 64:
        return "ERR"
    if len(lines) - 1 != k:
        return "ERR"

    prog = []
    for i in range(1, k + 1):
        parts = lines[i].split()
        if not parts:
            return "ERR"
        op = parts[0]
        if op == "PUSH":
            if len(parts) != 2:
                return "ERR"
            try:
                n = int(parts[1])
            except ValueError:
                return "ERR"
            prog.append(("PUSH", n))
        elif op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(parts) != 1:
                return "ERR"
            prog.append((op,))
        elif op == "JNZ":
            if len(parts) != 2:
                return "ERR"
            try:
                a = int(parts[1])
            except ValueError:
                return "ERR"
            prog.append(("JNZ", a))
        else:
            return "ERR"

    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        if pc < 0 or pc >= k:
            return "ERR"
        steps += 1
        if steps > 10000:
            return "ERR"
        ins = prog[pc]
        op = ins[0]
        if op == "PUSH":
            stack.append(ins[1])
            pc += 1
        elif op == "POP":
            if not stack:
                return "ERR"
            stack.pop()
            pc += 1
        elif op in ("ADD", "SUB", "MUL"):
            if len(stack) < 2:
                return "ERR"
            a = stack.pop()
            b = stack.pop()
            if op == "ADD":
                stack.append(b + a)
            elif op == "SUB":
                stack.append(b - a)
            else:
                stack.append(b * a)
            pc += 1
        elif op == "DUP":
            if not stack:
                return "ERR"
            stack.append(stack[-1])
            pc += 1
        elif op == "SWAP":
            if len(stack) < 2:
                return "ERR"
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op == "PRINT":
            if not stack:
                return "ERR"
            out.append(str(stack.pop()))
            pc += 1
        elif op == "JNZ":
            if not stack:
                return "ERR"
            v = stack.pop()
            if v != 0:
                a = ins[1]
                if a < 0 or a >= k:
                    return "ERR"
                pc = a
            else:
                pc += 1
        elif op == "HALT":
            return "\n".join(out)
